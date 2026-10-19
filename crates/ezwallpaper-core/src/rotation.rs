//! Pure content-ID shuffle-bag planning; callers own application and durable state.
use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashSet};

const SCHEMA_VERSION: u32 = 1;
const MAX_CANDIDATES: usize = 4_096;

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct RotationState {
    pub schema_version: u32,
    /// Highest acknowledged UTC epoch, not a local wall-clock hour.
    pub last_epoch: Option<i64>,
    pub last_content_id: Option<String>,
    /// Candidate IDs not yet used in this shuffle cycle.
    pub remaining: Vec<String>,
    pub cycle: u64,
}

impl Default for RotationState {
    fn default() -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            last_epoch: None,
            last_content_id: None,
            remaining: Vec::new(),
            cycle: 0,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum RotationDecision {
    Select,
    AlreadyApplied,
    EmptyPool,
    NoAlternative,
}

/// A read-only proposal. The caller may persist proposed_state only after an
/// explicitly acknowledged apply outcome. Planning alone has no side effects.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct RotationPlan {
    pub output: String,
    pub epoch: i64,
    pub decision: RotationDecision,
    pub content_id: Option<String>,
    pub proposed_state: Option<RotationState>,
}

fn valid_content_id(id: &str) -> bool {
    id.strip_prefix("sha256:")
        .map(|hex| {
            hex.len() == 64
                && hex
                    .bytes()
                    .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
        })
        .unwrap_or(false)
}

fn shuffled_candidates(output: &str, cycle: u64, ids: &BTreeSet<String>) -> Vec<String> {
    let mut ranked: Vec<([u8; 32], String)> = ids
        .iter()
        .map(|id| {
            let mut hasher = Sha256::new();
            hasher.update(b"ezwallpaper-shuffle-v1\0");
            hasher.update(output.as_bytes());
            hasher.update(b"\0");
            hasher.update(cycle.to_le_bytes());
            hasher.update(b"\0");
            hasher.update(id.as_bytes());
            let rank: [u8; 32] = hasher.finalize().into();
            (rank, id.clone())
        })
        .collect();
    ranked.sort();
    ranked.into_iter().map(|(_, id)| id).collect()
}

/// Selects a content ID without reading paths, consulting the clock, or
/// mutating state. Epochs should be integer UTC buckets provided by the caller.
///
/// A repeated or backward epoch remains unchanged unless force=true. Missing
/// hours are not replayed. Multiple candidates never repeat the previous
/// acknowledged content ID; empty and single-current pools report degradation.
pub fn plan_rotation(
    output: &str,
    epoch: i64,
    candidates: &[String],
    state: &RotationState,
    force: bool,
) -> Result<RotationPlan> {
    if output.trim().is_empty() || output.len() > 128 || output.chars().any(char::is_control) {
        bail!("rotation output name is invalid");
    }
    if state.schema_version != SCHEMA_VERSION {
        bail!("unsupported rotation state version");
    }
    if state.last_epoch.is_some() != state.last_content_id.is_some() {
        bail!("rotation state has inconsistent acknowledged fields");
    }
    if candidates.len() > MAX_CANDIDATES || state.remaining.len() > MAX_CANDIDATES {
        bail!("rotation candidate limit exceeded");
    }
    if state
        .last_content_id
        .as_deref()
        .map(|id| !valid_content_id(id))
        .unwrap_or(false)
        || candidates.iter().any(|id| !valid_content_id(id))
        || state.remaining.iter().any(|id| !valid_content_id(id))
    {
        bail!("rotation content IDs must be lowercase sha256 digests");
    }

    let unchanged = |decision: RotationDecision| RotationPlan {
        output: output.to_owned(),
        epoch,
        decision,
        content_id: state.last_content_id.clone(),
        proposed_state: None,
    };

    if !force && state.last_epoch.map(|last| epoch <= last).unwrap_or(false) {
        return Ok(unchanged(RotationDecision::AlreadyApplied));
    }

    let pool: BTreeSet<String> = candidates.iter().cloned().collect();
    if pool.is_empty() {
        return Ok(unchanged(RotationDecision::EmptyPool));
    }
    if pool.len() == 1 && pool.iter().next() == state.last_content_id.as_ref() {
        return Ok(unchanged(RotationDecision::NoAlternative));
    }

    let mut seen = HashSet::new();
    let mut remaining: Vec<String> = state
        .remaining
        .iter()
        .filter(|id| pool.contains(*id) && seen.insert((*id).clone()))
        .cloned()
        .collect();
    let mut cycle = state.cycle;

    if remaining.first() == state.last_content_id.as_ref() {
        if remaining.len() > 1 {
            remaining.swap(0, 1);
        } else {
            remaining.clear();
        }
    }
    if remaining.is_empty() {
        cycle = cycle
            .checked_add(1)
            .ok_or_else(|| anyhow::anyhow!("rotation cycle overflow"))?;
        remaining = shuffled_candidates(output, cycle, &pool);
        if remaining.first() == state.last_content_id.as_ref() && remaining.len() > 1 {
            remaining.swap(0, 1);
        }
    }

    let selected = remaining.remove(0);
    let proposed_state = RotationState {
        schema_version: SCHEMA_VERSION,
        last_epoch: Some(
            state
                .last_epoch
                .map(|last| last.max(epoch))
                .unwrap_or(epoch),
        ),
        last_content_id: Some(selected.clone()),
        remaining,
        cycle,
    };
    Ok(RotationPlan {
        output: output.to_owned(),
        epoch,
        decision: RotationDecision::Select,
        content_id: Some(selected),
        proposed_state: Some(proposed_state),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn id(digit: &str) -> String {
        format!("sha256:{}", digit.repeat(64))
    }

    #[test]
    fn a_day_of_epochs_never_repeats_adjacent_content() {
        let candidates = vec![id("a"), id("b"), id("c"), id("a")];
        let mut acknowledged = RotationState::default();
        let mut prior = None;
        for epoch in 0..48 {
            let plan = plan_rotation("DP-1", epoch, &candidates, &acknowledged, false)
                .expect("plan succeeds offline");
            assert_eq!(plan.decision, RotationDecision::Select);
            assert_ne!(plan.content_id, prior);
            assert!(candidates.contains(plan.content_id.as_ref().expect("candidate")));
            let retry = plan_rotation("DP-1", epoch, &candidates, &acknowledged, false)
                .expect("same state gives same proposal");
            assert_eq!(plan, retry);
            prior = plan.content_id.clone();
            // Only an acknowledged result advances the external state.
            acknowledged = plan.proposed_state.expect("pending acknowledged state");
            let same_epoch = plan_rotation("DP-1", epoch, &candidates, &acknowledged, false)
                .expect("same epoch idempotent");
            assert_eq!(same_epoch.decision, RotationDecision::AlreadyApplied);
            assert!(same_epoch.proposed_state.is_none());
        }
        assert!(acknowledged.cycle > 1);
        let restored: RotationState =
            serde_json::from_str(&serde_json::to_string(&acknowledged).expect("serialize state"))
                .expect("deserialize state");
        assert_eq!(restored, acknowledged);
    }

    #[test]
    fn single_and_empty_pool_never_claim_a_change() {
        let one = vec![id("a")];
        let first = plan_rotation("eDP-1", 1, &one, &RotationState::default(), false)
            .expect("first selection");
        assert_eq!(first.decision, RotationDecision::Select);
        let state = first.proposed_state.expect("acknowledged");
        let single = plan_rotation("eDP-1", 2, &one, &state, false).expect("single pool");
        assert_eq!(single.decision, RotationDecision::NoAlternative);
        assert!(single.proposed_state.is_none());
        let empty = plan_rotation("eDP-1", 3, &[], &state, false).expect("empty pool");
        assert_eq!(empty.decision, RotationDecision::EmptyPool);
        assert!(empty.proposed_state.is_none());
        let alternative =
            plan_rotation("eDP-1", 4, &[id("b")], &state, false).expect("new single image");
        assert_eq!(alternative.decision, RotationDecision::Select);
    }

    #[test]
    fn outputs_and_clock_rollback_are_independent() {
        let landscape = vec![id("a"), id("b")];
        let portrait = vec![id("c"), id("d")];
        let first = plan_rotation("DP-1", 100, &landscape, &RotationState::default(), false)
            .expect("landscape plan");
        let vertical = plan_rotation("HDMI-A-1", 100, &portrait, &RotationState::default(), false)
            .expect("portrait plan");
        assert_ne!(first.content_id, vertical.content_id);
        let acknowledged = first.proposed_state.expect("acknowledged");
        let rollback =
            plan_rotation("DP-1", 99, &landscape, &acknowledged, false).expect("clock rollback");
        assert_eq!(rollback.decision, RotationDecision::AlreadyApplied);
        let forced = plan_rotation("DP-1", 99, &landscape, &acknowledged, true)
            .expect("manual forced rotation");
        assert_eq!(forced.decision, RotationDecision::Select);
        assert_ne!(forced.content_id, acknowledged.last_content_id);
        assert_eq!(
            forced.proposed_state.expect("forced state").last_epoch,
            Some(100)
        );
    }

    #[test]
    fn shrinking_pool_does_not_select_removed_items() {
        let initial = vec![id("a"), id("b"), id("c")];
        let first = plan_rotation("DP-1", 1, &initial, &RotationState::default(), false)
            .expect("initial selection");
        let accepted = first.proposed_state.expect("accepted state");
        let available: Vec<String> = initial
            .iter()
            .filter(|candidate| Some((*candidate).as_str()) != accepted.last_content_id.as_deref())
            .cloned()
            .collect();
        let next =
            plan_rotation("DP-1", 2, &available, &accepted, false).expect("pool was reduced");
        assert!(available.contains(next.content_id.as_ref().expect("selected")));
        assert_ne!(next.content_id, accepted.last_content_id);
    }

    #[test]
    fn rejects_malformed_ids_state_and_output() {
        let good = id("a");
        assert!(plan_rotation("", 1, std::slice::from_ref(&good), &RotationState::default(), false).is_err());
        assert!(plan_rotation(
            "DP-1",
            1,
            &["fake".into()],
            &RotationState::default(),
            false
        )
        .is_err());
        let mut bad = RotationState {
            schema_version: 2,
            ..RotationState::default()
        };
        assert!(plan_rotation("DP-1", 1, std::slice::from_ref(&good), &bad, false).is_err());
        bad.schema_version = 1;
        bad.last_epoch = Some(5);
        assert!(plan_rotation("DP-1", 6, &[good], &bad, false).is_err());
    }
}

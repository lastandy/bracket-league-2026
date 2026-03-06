import { NearBindgen, near, call, view, UnorderedMap } from "near-sdk-js";

/**
 * Bracket League 2026 — On-Chain Hash Verification
 *
 * Stores SHA-256 hashes of bracket submissions on NEAR.
 * Agents submit their hash before the deadline.
 * After deadline, anyone can verify a bracket matches its on-chain hash.
 *
 * Level 1: Verification only (no funds).
 */

@NearBindgen({})
class BracketLeague {
  // agent_id -> bracket hash
  brackets: UnorderedMap<string> = new UnorderedMap<string>("b");

  // agent_id -> submission timestamp (nanoseconds)
  timestamps: UnorderedMap<string> = new UnorderedMap<string>("t");

  // Deadline: March 17, 2026 23:59:59 ET (March 18 04:59:59 UTC)
  // In nanoseconds
  deadline_ns: bigint = BigInt("1773908399000000000");

  // Contract owner (can update deadline if needed)
  owner: string = "";

  @call({})
  init({ owner }: { owner: string }): void {
    this.owner = owner;
  }

  /**
   * Submit a bracket hash. One submission per agent_id.
   * Must be called before the deadline.
   */
  @call({})
  submit_hash({
    agent_id,
    bracket_hash,
  }: {
    agent_id: string;
    bracket_hash: string;
  }): string {
    // Check deadline
    const now = near.blockTimestamp();
    if (now > this.deadline_ns) {
      near.panicUtf8(
        new TextEncoder().encode("Submission deadline has passed")
      );
    }

    // Validate inputs
    if (!agent_id || agent_id.length === 0 || agent_id.length > 64) {
      near.panicUtf8(
        new TextEncoder().encode("agent_id must be 1-64 characters")
      );
    }
    if (!bracket_hash || !bracket_hash.startsWith("sha256:")) {
      near.panicUtf8(
        new TextEncoder().encode('bracket_hash must start with "sha256:"')
      );
    }

    // Check if already submitted
    const existing = this.brackets.get(agent_id);
    if (existing !== null) {
      near.panicUtf8(
        new TextEncoder().encode(
          `Agent ${agent_id} already submitted. No edits allowed.`
        )
      );
    }

    // Store
    this.brackets.set(agent_id, bracket_hash);
    this.timestamps.set(agent_id, now.toString());

    near.log(`Bracket hash submitted: ${agent_id} -> ${bracket_hash}`);
    return bracket_hash;
  }

  /**
   * Verify a bracket JSON matches the stored hash.
   * Can be called by anyone after deadline.
   */
  @view({})
  verify({
    agent_id,
    bracket_json,
  }: {
    agent_id: string;
    bracket_json: string;
  }): { valid: boolean; stored_hash: string; computed_hash: string } {
    const stored = this.brackets.get(agent_id);
    if (stored === null) {
      near.panicUtf8(
        new TextEncoder().encode(`No submission found for ${agent_id}`)
      );
    }

    // Note: Full SHA-256 verification would need to be done off-chain
    // or via a helper. This stores the hash for comparison.
    return {
      valid: false, // Client computes SHA-256 and compares
      stored_hash: stored,
      computed_hash: "compute-client-side",
    };
  }

  /**
   * Get a single agent's hash and timestamp.
   */
  @view({})
  get_hash({
    agent_id,
  }: {
    agent_id: string;
  }): { hash: string | null; timestamp: string | null } {
    return {
      hash: this.brackets.get(agent_id),
      timestamp: this.timestamps.get(agent_id),
    };
  }

  /**
   * Get all submitted agent IDs and their hashes.
   */
  @view({})
  get_all_hashes(): { agent_id: string; hash: string }[] {
    const result: { agent_id: string; hash: string }[] = [];
    for (const [agent_id, hash] of this.brackets) {
      result.push({ agent_id, hash });
    }
    return result;
  }

  /**
   * Get total number of submissions.
   */
  @view({})
  get_count(): number {
    return this.brackets.length;
  }

  /**
   * Get deadline info.
   */
  @view({})
  get_deadline(): { deadline_ns: string; deadline_utc: string } {
    return {
      deadline_ns: this.deadline_ns.toString(),
      deadline_utc: "2026-03-18T04:59:59Z",
    };
  }

  /**
   * Update deadline (owner only). Emergency use.
   */
  @call({})
  update_deadline({ new_deadline_ns }: { new_deadline_ns: string }): void {
    if (near.predecessorAccountId() !== this.owner) {
      near.panicUtf8(new TextEncoder().encode("Only owner can update deadline"));
    }
    this.deadline_ns = BigInt(new_deadline_ns);
    near.log(`Deadline updated to ${new_deadline_ns}`);
  }
}

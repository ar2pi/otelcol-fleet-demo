# Typical gcx workflow

[gcx](https://github.com/grafana/gcx) is Grafana Cloud's CLI. Its `fleet`
provider talks to the same Fleet Management API as the GitOps sync in this
repo, which makes it the right tool for the two things git is bad at:
**inspecting live fleet state** and **break-glass changes during an incident**.

Rule of thumb for this repo:

| Task | Tool |
|---|---|
| Durable config changes | PR to `pipelines/` (GitOps sync) |
| Inspecting collectors, effective config, pipeline state | `gcx fleet ...` (read) |
| Temporary/emergency changes | `gcx fleet pipelines ...` (write, see caveats) |

## 0. One-time setup

```sh
# Point a context at your stack and authenticate
gcx config set contexts.fleet-demo.grafana.server https://<your-stack>.grafana.net
gcx config set contexts.fleet-demo.cloud.stack <your-stack>
gcx config use-context fleet-demo

# The fleet provider needs a Grafana Cloud token; the CI token
# (fleet-management:write) from the README works
gcx config set cloud.token <TOKEN>     # or: export GRAFANA_CLOUD_TOKEN=<TOKEN>

# Verify before doing anything
gcx config check
```

Use `--context fleet-demo` on any command instead of `use-context` if you
juggle multiple stacks.

## 1. Inspect the fleet

```sh
# All collectors with health and attributes — the three demo collectors
# show up here once `make up` is running
gcx fleet collectors list

# Drill into one: attributes, health, which pipelines matched
gcx fleet collectors get collector-prod-checkout -o yaml

# What configuration is deployed right now?
gcx fleet pipelines list
gcx fleet pipelines get baseline-hostmetrics -o yaml

# Tenant quotas (pipeline/collector limits)
gcx fleet tenant limits
```

Handy for scripting — every command takes `-o json` and `--json` field
selection (`--json '?'` lists available fields):

```sh
gcx fleet collectors list -o json --json 'name,attributes' | jq .
```

## 2. Verify a GitOps sync landed

After merging a change to `pipelines/`:

```sh
# Compare what's deployed against what's in git
gcx fleet pipelines get dev-otlp-debug -o yaml
git show main:pipelines/dev-otlp-debug.yaml
```

## 3. Break-glass: ad-hoc pipeline during an incident

Scenario: the `checkout` team's collectors are misbehaving and you want
detailed debug output from them *now*, without waiting for a PR cycle.

Two routes, depending on the pipeline type. As of gcx fleet provider
`v1alpha1`, `gcx fleet pipelines create` **only accepts Alloy-type
pipelines** — contents are validated as Alloy (River) syntax and names must be
valid Alloy identifiers (underscores, no dashes). OTel-type pipelines (what
this demo's collectors run) go through the Pipeline API instead.

Both canary manifests live in `examples/`, not `pipelines/`, so the GitOps
sync never deploys or deletes them.

### 3a. OTel fleet (this demo) — via the Pipeline API

[`examples/canary-checkout-debug.yaml`](../examples/canary-checkout-debug.yaml)
targets only `team="checkout"`:

```sh
# 1. Read current state first
gcx fleet pipelines list

# 2. Create the canary (FM_API_TOKEN = the fleet-management:write token)
FM_API_TOKEN=<token> ./scripts/upsert-pipeline.py examples/canary-checkout-debug.yaml

# 3. Verify it deployed and only matched checkout collectors
gcx fleet pipelines get canary-checkout-debug -o yaml
gcx fleet collectors get collector-prod-checkout -o yaml

# 4. Investigate (make logs shows the extra debug output on checkout
#    collectors only), then clean up
FM_API_TOKEN=<token> ./scripts/upsert-pipeline.py --delete canary-checkout-debug
```

### 3b. Alloy fleet — pure gcx

gcx expects the k8s-style resource manifest (`apiVersion`/`kind`/`metadata`/
`spec`) — discover the format with `gcx resources examples pipelines -o yaml`.
[`examples/canary-alloy-debug.yaml`](../examples/canary-alloy-debug.yaml) is
ready to go:

```sh
gcx fleet pipelines create -f examples/canary-alloy-debug.yaml
gcx fleet pipelines get canary_checkout_debug -o yaml
gcx fleet pipelines delete canary_checkout_debug
```

## Caveats: gcx writes vs GitOps

- **Don't `gcx fleet pipelines update` a pipeline that lives in `pipelines/`.**
  The repo is the source of truth: the next merge touching `pipelines/**`
  re-syncs and silently reverts your out-of-band edit. If a change should
  stick, make it a PR.
- Ad-hoc pipelines created with gcx (like the canary) are outside the
  `otelcol-fleet-demo` sync namespace, so the GitHub Action won't delete
  them — but that also means *you* own their cleanup.
- Give ad-hoc pipelines an obvious prefix (`canary-`, `incident-`) so they're
  easy to spot and reap in `gcx fleet pipelines list`.
- `gcx fleet pipelines/collectors get <name>` resolves the *registered* name
  (`spec.name`, e.g. `collector-prod-checkout`), not the synthetic
  `metadata.name` shown by `list` (e.g. `resource-82c42b...`,
  `canary-checkout-debug-13135`).

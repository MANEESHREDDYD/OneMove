from pydantic import StrictInt, StrictStr

from services.api.contracts.observatory import StrictContract


class GoldReleaseIdentity(StrictContract):
    dataset_id: StrictStr
    dataset_version: StrictStr
    schema_version: StrictStr
    artifact_sha256: StrictStr
    record_count: StrictInt


class GraphReleaseIdentity(StrictContract):
    graph_version: StrictStr
    topology_sha256: StrictStr
    bundle_sha256: StrictStr


class ReleaseIdentity(StrictContract):
    app_version: StrictStr
    git_sha: StrictStr
    schema_version: StrictStr
    gold: GoldReleaseIdentity
    graph: GraphReleaseIdentity


class ReleaseIdentityResponse(StrictContract):
    data: ReleaseIdentity

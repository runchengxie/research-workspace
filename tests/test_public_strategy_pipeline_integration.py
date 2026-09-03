from strategy_pipeline import ArtifactRef, PublicationRequest, RunRequest, run


def test_workspace_can_use_public_control_plane_without_strategy_dependencies():
    produced = ArtifactRef(
        kind="workspace.synthetic",
        uri="memory://workspace/synthetic.json",
        digest="sha256:workspace",
        producer="research-workspace-test-owner",
    )
    published = ArtifactRef(
        kind="workspace.synthetic",
        uri="memory://workspace/published.json",
        digest="sha256:workspace",
        producer="research-workspace-test-publisher",
    )

    class Owner:
        def run(self, request: RunRequest) -> ArtifactRef:
            return produced

    class Publisher:
        def publish(self, request: PublicationRequest) -> ArtifactRef:
            return published

    receipt = run(RunRequest("workspace-run", ()), owner=Owner(), publisher=Publisher())

    assert receipt.status == "published"
    assert receipt.artifacts == (published,)

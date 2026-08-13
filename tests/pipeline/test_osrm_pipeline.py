from unittest.mock import Mock

from services.routing import osrm_pipeline


def test_run_docker_osrm_maps_posix_host_user(monkeypatch):
    run = Mock()
    monkeypatch.setattr(osrm_pipeline.os, "getuid", lambda: 1001, raising=False)
    monkeypatch.setattr(osrm_pipeline.os, "getgid", lambda: 1002, raising=False)
    monkeypatch.setattr(osrm_pipeline.subprocess, "run", run)

    osrm_pipeline.run_docker_osrm("osrm-partition", "/data/pilot_roads.osrm")

    command = run.call_args.args[0]
    assert command[:5] == ["docker", "run", "-t", "--user", "1001:1002"]
    assert command[-2:] == ["osrm-partition", "/data/pilot_roads.osrm"]
    assert run.call_args.kwargs == {"check": True}

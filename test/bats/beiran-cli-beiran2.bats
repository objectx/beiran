#!/usr/bin/env bats

@test "pull alpine from other node" {
    run beiran --config /etc/beiran/config.toml docker image pull alpine
    [ "$status" -eq 0 ]
}

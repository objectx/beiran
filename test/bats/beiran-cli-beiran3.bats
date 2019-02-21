#!/usr/bin/env bats

@test "pull alpine from other node (with '--wait' option)" {
    run beiran --config /etc/beiran/config.toml docker image pull alpine --wait
    [ "$status" -eq 0 ]
}

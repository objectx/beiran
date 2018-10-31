#!/usr/bin/env bats

@test "pull alpine from other node" {
    run python -m beiran docker image pull alpine
    [ "$status" -eq 0 ]
}

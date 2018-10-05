#!/usr/bin/env bats

@test "pull alpine from other node" {
    run python -m beiran docker image pull alpine
    [ "$status" -eq 0 ]
}

@test "pull alpine from other node (with '--wait' option)" {
    run python -m beiran docker image pull alpine --wait
    [ "$status" -eq 0 ]
}

@test "pull alpine from other node (with '--progress' option)" {
    run python -m beiran docker image pull alpine --progress
    [ "$status" -eq 0 ]
}

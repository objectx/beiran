#!/usr/bin/env bats

@test "pull nginx from other node" {
    run python -m beiran docker image pull nginx
    [ "$status" -eq 0 ]
}

@test "pull nginx from other node (with '--wait' option)" {
    run python -m beiran docker image pull nginx --wait
    [ "$status" -eq 0 ]
}

@test "pull nginx from other node (with '--progress' option)" {
    run python -m beiran docker image pull nginx --progress
    [ "$status" -eq 0 ]
}

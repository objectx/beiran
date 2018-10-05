#!/usr/bin/env bats

@test "pull alpine from other node (with '--progress' option)" {
    run python -m beiran docker image pull alpine --progress
    [ "$status" -eq 0 ]
}

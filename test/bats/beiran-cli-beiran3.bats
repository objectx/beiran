#!/usr/bin/env bats

@test "pull alpine from other node (with '--wait' option)" {
    run python -m beiran docker image pull alpine --wait
    [ "$status" -eq 0 ]
}

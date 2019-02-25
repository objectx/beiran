#!/usr/bin/env bats

@test "pull alpine from other node (with '--progress' option)" {
    run beiran docker image pull alpine --progress
    [ "$status" -eq 0 ]
}

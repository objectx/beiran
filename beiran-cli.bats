#!/usr/bin/env bats

@test "pull alpine from other node" {
    run python -m beiran docker image pull alpine && sleep 5
    [ "$status" -eq 0 ]
}

@test "pull alpine from other node (with '--wait' option)" {
    run docker rmi alpine && python -m beiran docker image pull alpine --wait && sleep 1
    [ "$status" -eq 0 ]
}

@test "pull alpine from other node (with '--progress' option)" {
    run docker rmi alpine && python -m beiran docker image pull alpine --progress
    [ "$status" -eq 0 ]
}

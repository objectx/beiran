#!/usr/bin/env bats

@test "pull nginx from other node" {
    run python -m beiran docker image pull nginx && sleep 5
    [ "$status" -eq 0 ]
}

@test "pull nginx from other node (with '--wait' option)" {
    run docker rmi nginx && python -m beiran docker image pull nginx --wait && sleep 1
    [ "$status" -eq 0 ]
}

@test "pull nginx from other node (with '--progress' option)" {
    run docker rmi nginx && python -m beiran docker image pull nginx --progress
    [ "$status" -eq 0 ]
}

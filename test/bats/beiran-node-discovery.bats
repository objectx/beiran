#!/usr/bin/env bats

@test "Check if nodes discover each other correctly" {
    python -m beiran.cli node list |  wc -l
    [ "$output" -eq "6" ]
}
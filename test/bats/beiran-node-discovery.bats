#!/usr/bin/env bats

@test "Check if nodes discover each other correctly" {
    grep -R1 "sqlite3 /var/lib/beiran/beiran.db 'select * from node'" ./ -c
    [ $output = 4 ]
}
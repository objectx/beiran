
See the [issues](https://git.rlab.io/poc/beiran/issues)

## v0.0.0

 - [x] Team Arrangements
 - [x] Dev Environment
 - [x] Initial Investigations

## v0.0.1

Main Objectives:
 - ...

## v0.0.2

 - [x] lib: ORM/Database setup
 - [x] event emitter pattern

## v0.0.3

Main Objectives:
 - ...

## v0.0.4

Main Objectives:
 - Nodes detect each other
 - CLI is able to list detected node information, etc.

Tasks:
 - [x] daemon/discovery: dns discovery module
 - [x] lib: Node Model
 - [x] daemon: daemon wide access to active node list
 - [x] daemon/init
   - [x] generate uuid {config_folder:-/etc/beiran}/node.uuid
   - [x] create database structure on init (if necessary)
 - [x] api: /info endpoint
 - [ ] beirand: when a node is discovered, throw a daemon-wide event `new-node`
 - [ ] beirand: with a listener on `new-node` event, probe that node's `/info` endpoint, and record collected info into local database
 - [ ] api: /nodes endpoint: list known nodes and their information
   - /nodes?all=true returns all known nodes, by default only online nodes are returned?
 - [ ] lib: beiran.Client.get_online_nodes method
 - [ ] lib: beiran.Client.get_known_nodes method
 - [ ] cli: `beiran node list --all` (known)
 - [ ] cli: `beiran node list` (online only)

## v0.0.5

Main Objectives:
 - Nodes populate their local database with other nodes layer & image lists

## v0.0.6

Main Objectives:
 - ...

## v0.0.7

Main Objectives:
 - ...

## v0.0.8

Main Objectives:
 - ...

## v0.0.9

Main Objectives:
 - ...

## v0.1.0 (poc)

Main Objectives:
 - nodes share their image/layer/metadata information on demand
 - nodes share the download work amongs them, reducing overall redundant bandwidth usage

 - [ ] beirand: api endpoints (to be listed here one by one)

 - [ ] beirand: tcp socket for http
 - [ ] beirand: websocket over tcp/http
 - [ ] beirand: local unix socket (http) for client communication
 - [ ] beiran-cli: local unix socket connection to beirand
 - [ ] folder structure

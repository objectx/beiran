# beiran roadmap

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

## [v0.0.4](https://git.rsnc.io/rlab/beiran/issues?state=open&milestone=1)

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
 - [x] #5 & #9 beirand: when a node is discovered, throw a daemon-wide event `new-node`
 - [x] #5 beirand: with a listener on `new-node` event, probe that node's `/info` endpoint, and record collected info into local database
 - [x] #5 api: /nodes endpoint: list known nodes and their information
   - /nodes?all=true returns all known nodes, by default only online nodes are returned?
 - [x] #10 lib: beiran.Client.get_online_nodes method
 - [x] #10 lib: beiran.Client.get_known_nodes method
 - [x] #8 cli: `beiran node list --all` (known)
 - [x] #8 cli: `beiran node list` (online only)

## [v0.0.5](https://git.rsnc.io/rlab/beiran/issues?state=open&milestone=2)

Main Objectives:
 - Sharing image and layer list between nodes and updating image/layer database

 - [x] #14 lib: finalize layer and image models (enough for this milestone)
   - for now we don't need anything other than docker's format
   - we need to be able to store which nodes have which images and layers
   - some of images and layers might already exist in the local database, add information that this node also has those images/layers.
   - Possession model?
     - just keep in the original model in some json array property.
       like; `image.available_at = '[ "beiran+tcp://17.18.0.1:8888", "beiran+uuid://3c8b816d-b723-41e1-a0c8-59ef254bef51" ]'` ??
       - we should only use uuid scheme here for now, to be able to provide the following;
         - `beiran image list --node=3c8b816d-b723-41e1-a0c8-59ef254bef51`
 - [ ] #15 daemon: on `node.added` fetch image and layers from new discovered node, and save the list into local database
 - [ ] #16 api: /images listing endpoint
   - [ ] api: /images?all=true listing endpoint (for cli or local client access)
 - [ ] #17 api: /layers listing endpoint  (can actually deliver payload at this moment)
   - [ ] api: /layers?all=true listing endpoint (for cli or local client access)
 - [ ] #16 & #17 api: /images|layers?node=3c8b816d-b723-41e1-a0c8-59ef254bef51 listing endpoint
 - [ ] #18 lib: methods for fetching image list
 - [ ] #19 lib: methods for fetching layer list
 - [ ] #20 cli: `beiran image list` (probing local beiran daemon for local docker's only)
   - [ ] cli: `beiran image list --all` (asking local beiran daemon to give all images between connected peers)
 - [ ] #21 cli: `beiran layer list` (probing local beiran daemon for local docker's only)
   - [ ] cli: `beiran layer list --all` (asking local beiran daemon to give all images between connected peers)
   - [ ] cli: `beiran image list --node=3c8b816d-b723-41e1-a0c8-59ef254bef51` to query images hold by a specific node

## [v0.0.5-tests](https://git.rsnc.io/rlab/beiran/issues?state=open&milestone=8)
 - [ ] end to end behavior tests for expected flows
   - mock the initial state
     - have a docker daemon
     - have specific images and layers in docker daemon
     - check the expected result in final cli command invoke, which would check the functionality all layers in between
 - [x] behavior tests for http/api interface?
   - pyresttest?
 - [ ] behavior tests for library interface?
   - pytest?
 - [ ] unit tests for internal daemon behavior? (events, etc?)
   - (draft) daemon-wide events are emitted correctly?
   - (draft) ..

 - [ ] #11 TASK: "Document our test scenarios" (@s-yamada ?)
   - Go through the code and components
   - Expected results:
     - List necessary types of testing
     - List necessary components and behaviors to be tested
   - [ ] #12 create issues in `v0.0.5-tests`
   - [ ] #13 after: create sample working (real) tests for each test category/system
     - behave
     - pyresttest
     - e2e/shell?

 - INSPECT: https://github.com/behave/behave ?

 - [x] TASK: "Document usage"

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

# Sruput - Container Builder Workflow

Simple Container Build & Release using GitHub Action Workflow.

This template is used to immediately copy a workflow in this repo to make your own builder for your custom project.

## How to use

Simply copy the workflow and create a minimal config file called `sruput.yaml`. 
The file should point to your build/release matrix or parameters.

## Behaviour

Sruput GH Action will read the config file and then you can use the processed output for your 
other action.

### Main use case: for a docker build release

This is an example for the workflow to build and release docker image :

```yaml
name: latest-build
on:
  workflow_dispatch:
    inputs:
      tags:
        description: 'Git tag to use'
  pull_request:
    branches:
      - develop
      - main
  push:
    branches:
      - develop
      - main
    tags:
      - '*.*.*.'
jobs:
  build-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        image-variant:
          - debian
          - alpine
        image-target:
          - prod
          - dev
    env:
      APP_IMAGE: lucernae/myapp
    steps:
      - uses: actions/checkout@v2
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v1
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v1
      - name: Login to DockerHub
        uses: docker/login-action@v1
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_PASSWORD }}
      - name: Sruput docker context
        id: sruput_docker_meta
        uses: lucernae/sruput-action@v1
      - name: Docker meta
        id: docker_meta
        uses: docker/metadata-action@v3
        with:
          images: ${{ steps.sruput_docker_meta.outputs.repo_owner }}/${{ steps.sruput_docker_meta.outputs.repo_name }}
          tags: |
            type=semver,pattern=\d.\d.\d
            type=ref,event=branch
            type=ref,event=pr
      - name: Sruput docker build
        id: sruput_docker_build
        uses: lucernae/sruput-action@v1
        with:
          param: |
            docker-meta-tags: ${{ steps.docker_meta.outputs.tags}}
            variant: ${{ matrix.image-variant }}
            target: ${{ matrix.image-target }}
      - name: Build image
        uses: docker/build-push-action@v2
        with:
          context: .
          file: ${{ steps.sruput_docker_build.outputs.dockerfile }}
          push: ${{ steps.sruput_docker_build.outputs.push }}
          load: ${{ steps.sruput_docker_build.outputs.load }}
          target: ${{ steps.sruput_docker_build.outputs.target }}
          tags: ${{ steps.sruput_docker_build.outputs.tags }}
          cache-from: |
            type=gha,scope=${{ steps.sruput_docker_build.outputs.target }}
          cache-to: type=gha,scope=${{ steps.sruput_docker_build.outputs.target }}
```

In the above workflow, the final step is to build and push a docker image. 
However the decision and parameters of the build depends on the context collected
by the Sruput action. How Sruput collect this meta information depends on the file
described in `sruput.yaml`.

```yaml
repo-owner:
  - type: github-action
    context-path: 'github.repository_owner'
repo-name: 
  - type: github-action
    context-path: 'github.repository.name'
variant:
target:
full-variant-name:
  - scalar: '{param["variant"]}--{param["target"]}'
  # If it contains 'prod' target, omit it, because it's the default.
  - type: replace
    regex-match: '--prod'
    regex-replace: ''
    input: '{param["full-variant-name"]}'
calver:
  - type: datetime
    format: '%Y.%m.%d'
tags:
  - and:
      - type: replace
        regex-match: 'develop'
        regex-replace: 'latest'
        input: '{param["docker-meta-tags"]}'
      - type: replace
        regex-match: 'main'
        regex-replace: 'stable'
        input: '{param["docker-meta-tags"]}'
      # image tag for a semver release +
      # image tag for canonical release (with added calver segments)
      - type: replace
        regex-match: '(\d.\d.\d)'
        regex-replace: |
          {param["full-variant-name"]}--\\1
          {param["full-variant-name"]}--\\1--{param["calver"]}
        input: '{param["docker-meta-tags"]}'
dockerfile:
  - scalar: 'variants/{param["variant"]}/Dockerfile'
push:
  # we can only push if it is commit changes of the same repo or
  # PR from the same repository.
  - equal:
      - scalar: '{github.event.pull_request.base.repo.url}'
      - scalar: '{github.event.pull_request.head.repo.url}'
load:
  - scalar: false
```

By separating the meta context and the workflows, we decoupled the rule-based inference with the action itself.
This way, you can refactor both separately. You can use the approach to organize the same rules of meta-handling via `sruput.yaml`.
If in the future your action needs update, you can refactor it easily, or let bot do that.
The merit works both ways. If there are new repo and you want to enforce the same meta-handling rules, you just need to copy `sruput.yaml`.
One central entity in your org then can easily check using automated tools if a repo is conformant with the current applied settings.

### Optional Use Case: Git Release

Normally you create a git release or tags by yourself. For big project with composite dependencies, it is often useful to decouple the 
workflow to create a release, with the PR to prepare the release.

The benefit of this approach:
 - Release manager can create a PR and then fill in the release details, such as:
    - Changelogs
    - Software version and metadata to be extracted by workflows
 - Git tag and release information is extracted from the metadata within the repo itself
 - Simplify Release Approval by discussion in the PR
 - Can be hooked to an automatic action to immediately publish the release (or schedule it) via workflow on PR merge
 - `sruput.yaml` can act as a linter or dry-running the release process by checking the resulting metadata

A Git release usually express a snapshot of the repo as a certain tag. This make it a simpler case compared with previous example.
In the Docker image release workflow above, one repo can output several packages variants from the same source code, because their 
dependencies are different. In this example, we only output certain product, which is a git tag and github release.
An example workflow action to create a Github Release.

```yaml
name: 'auto-release'
on:
  push:
    paths:
      # List a file as triggers to tell that we should make a new tag
      - 'action.yaml'
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: lucernae/sruput-action@v1
        id: meta
        uses:
          config: sruput-release.yaml
      - uses: actions/github-script@v4
        with:
          script: |
            github.git.createTag({
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: '${{ steps.meta.outputs.tag }}',
              object: context.sha,
              type: 'commit'
            })
```

The corresponding `sruput-release.yaml` need to provides a rule to extract the tag.

```yaml
config:
  - type: yaml
    file: metadata.yaml
tag:
  - scalar: '{param["config"]["version"]}'
```
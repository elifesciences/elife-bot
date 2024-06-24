elifePipeline {
    def commit
    stage 'Checkout', {
        checkout scm
        commit = elifeGitRevision()
    }

    stage 'Project tests', {
        lock('elife-bot--ci') {
            builderDeployRevision 'elife-bot--ci', commit
            // execute and fail immediately if red, without waiting to download test artifacts
            builderCmd 'elife-bot--ci', 'cd /opt/elife-bot; ./project_tests.sh'

            // part of the bot test suite is a series of lettuce processes which cannot produce a single XML report
            // until there is a single test suite, we won't have XML test artifacts in the bot
            //def testArtifact = "${env.BUILD_TAG}.junit.xml"
            //builderTestArtifact testArtifact, 'elife-bot--ci', '/opt/elife-bot/build/junit.xml'
            //elifeVerifyJunitXml testArtifact
        }
    }

    elifeMainlineOnly {
        stage 'End2end tests', {
            elifeSpectrum(
                deploy: [
                    stackname: 'elife-bot--end2end',
                    revision: commit,
                    folder: '/opt/elife-bot',
                ],
                marker: 'bot'
            )
        }

        stage 'Deploy on continuumtest', {
            lock('elife-bot--continuumtest') {
                builderDeployRevision 'elife-bot--continuumtest', commit
                builderSmokeTests 'elife-bot--continuumtest', '/opt/elife-bot'
            }
        }

        stage 'Approval', {
            // June 24, 2024: to avoid the following error (#8844):
            // > error: pathspec 'approved' did not match any file(s) known to git.
            sh 'git config --add remote.origin.fetch +refs/heads/*:refs/remotes/origin/*'
            elifeGitMoveToBranch commit, 'approved'
        }
    }
}

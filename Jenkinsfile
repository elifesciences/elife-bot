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
                marker: 'continuum'
            )
        }

        stage 'Deploy on continuumtest', {
            lock('elife-bot--continuumtest') {
                builderDeployRevision 'elife-bot--continuumtest', commit
                builderSmokeTests 'elife-bot--continuumtest', '/opt/elife-bot'
            }
        }

        stage 'Approval', {
            elifeGitMoveToBranch commit, 'approved'
        }
    }
}

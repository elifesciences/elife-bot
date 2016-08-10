elifePipeline {
    stage 'Checkout'
    checkout scm
    def commit = elifeGitRevision()

    stage 'Project tests'
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

    elifeMainlineOnly {
        stage 'End2end tests'
        elifeEnd2EndTest {
            builderDeployRevision 'elife-bot--end2end', commit
        }

        stage 'Approval'
        elifeGitMoveToBranch commit, 'approved'
    }
}

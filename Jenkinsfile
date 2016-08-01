elifePipeline {
    stage 'Checkout'
    checkout scm
    def commit = elifeGitRevision()

    echo "env.BUILDER_SCRIPTS_PREFIX"
    echo env.BUILDER_SCRIPTS_PREFIX

    stage 'Project tests'
    lock('elife-bot--ci') {
        def stacknameCi = 'elife-bot-develop-ci'
        def testArtifact = "${env.BUILD_TAG}.junit.xml"
        elifeSwitchRevision stacknameCi, commit
        elifeCmd stacknameCi, 'cd /opt/elife-bot; ./project_tests.sh' // || echo TESTS FAILED!'
        // part of the bot test suite is a series of lettuce processes which cannot produce a single XML report
        // until there is a single test suite, we won't have XML test artifacts in the bot
        //elifeTestArtifact testArtifact, stacknameCi, '/opt/elife-bot/build/junit.xml'
        //elifeVerifyJunitXml testArtifact
    }

    elifeMainlineOnly {
        stage 'End2end tests'
        elifeEnd2EndTest {
            elifeSwitchRevision 'elife-bot-develop--end2end', commit
        }

        stage 'Approval'
        elifeGitMoveToBranch commit, 'approved'
    }
}

// One resumable slice of the Bastion Windows build.
// Adapted from ungoogled-chromium-windows/.github/actions/stage/index.js.
import * as core from '@actions/core';
import * as io from '@actions/io';
import * as exec from '@actions/exec';
import { DefaultArtifactClient } from '@actions/artifact';
import * as glob from '@actions/glob';

const BUILD_TIMEOUT_EXIT_CODE = 124;
const REPO = 'C:\\bastion';
const WORKDIR = 'C:\\bastion\\work';
const BUILD_DIR = `${WORKDIR}\\build`;
const PROGRESS_ARTIFACT = 'build-progress-x64';
const PACKAGE_ARTIFACT = 'bastion-x64';

async function uploadWithRetry(artifact, name, files, rootDir) {
    for (let i = 0; i < 5; ++i) {
        try { await artifact.deleteArtifact(name); } catch (e) { /* not there yet */ }
        try {
            await artifact.uploadArtifact(name, files, rootDir, { retentionDays: 4, compressionLevel: 0 });
            return;
        } catch (e) {
            console.error(`Artifact upload failed (attempt ${i + 1}/5): ${e}`);
            await new Promise(r => setTimeout(r, 10000));
        }
    }
    throw new Error(`Could not upload artifact ${name}`);
}

async function run() {
    // Upstream's build script stops ninja with Ctrl+C at the time limit; ignore it here.
    process.on('SIGINT', () => {});
    const finished = core.getBooleanInput('finished', { required: true });
    const fromArtifact = core.getBooleanInput('from_artifact', { required: true });
    console.log(`finished: ${finished}, resume from artifact: ${fromArtifact}`);
    if (finished) {
        core.setOutput('finished', true);
        return;
    }

    const artifact = new DefaultArtifactClient();

    if (fromArtifact) {
        await io.mkdirP(BUILD_DIR);
        await exec.exec(process.execPath, [`${import.meta.dirname}\\download.js`, PROGRESS_ARTIFACT, BUILD_DIR]);
        await exec.exec('7z', ['x', `${BUILD_DIR}\\artifacts.zip`, `-o${BUILD_DIR}`, '-y']);
        await io.rmRF(`${BUILD_DIR}\\artifacts.zip`);
    }

    // Same helper packages upstream installs for its build.
    await exec.exec('python', ['-m', 'pip', 'install', 'httplib2==0.22.0', 'clang==21.1.7'],
        { cwd: REPO, ignoreReturnCode: true });

    const retCode = await exec.exec('python',
        ['build.py', '--workdir', WORKDIR, '--ci', '-j', '2'],
        { cwd: REPO, ignoreReturnCode: true });

    if (retCode === 0) {
        const globber = await glob.create(`${BUILD_DIR}\\bastion_*`, { matchDirectories: false });
        const packages = await globber.glob();
        if (packages.length < 2) {
            throw new Error(`Build finished but packaging produced ${packages.length} file(s): ${packages}`);
        }
        await uploadWithRetry(artifact, PACKAGE_ARTIFACT, packages, BUILD_DIR);
        core.setOutput('finished', true);
    } else if (retCode === BUILD_TIMEOUT_EXIT_CODE) {
        // Out of time for this stage: save the half-built tree for the next one.
        await new Promise(r => setTimeout(r, 5000));
        await exec.exec('7z', ['a', '-tzip', `${WORKDIR}\\artifacts.zip`, `${BUILD_DIR}\\src`, '-mx=3', '-mtc=on'],
            { ignoreReturnCode: true });
        await uploadWithRetry(artifact, PROGRESS_ARTIFACT, [`${WORKDIR}\\artifacts.zip`], WORKDIR);
        core.setOutput('finished', false);
    } else {
        throw new Error(`Build failed with exit code ${retCode}`);
    }
}

run().catch(err => core.setFailed(err.message));

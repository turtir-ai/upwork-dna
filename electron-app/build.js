/**
 * Upwork DNA - Build Script
 * Prepares the app for packaging
 */

const fs = require('fs');
const path = require('path');

console.log('[Build] Preparing Upwork DNA for packaging...');

// Create symbolic links to extension and analist directories
const dirs = [
  { src: '../original_repo_v2', dest: './extension' },
  { src: '../analist', dest: './analist' },
  { src: '../upwork_dna', dest: './upwork_dna' }
];

dirs.forEach(dir => {
  const srcPath = path.resolve(__dirname, dir.src);
  const destPath = path.resolve(__dirname, dir.dest);

  try {
    // Remove existing link/dir
    if (fs.existsSync(destPath)) {
      fs.rmSync(destPath, { recursive: true, force: true });
    }

    // Create symbolic link (or copy on Windows)
    if (process.platform === 'win32') {
      // Windows: copy directory
      copyDirectory(srcPath, destPath);
    } else {
      // Unix: create symlink
      fs.symlinkSync(srcPath, destPath, 'dir');
    }

    console.log(`[Build] Linked: ${dir.dest}`);
  } catch (err) {
    console.error(`[Build] Error linking ${dir.dest}:`, err.message);
  }
});

function copyDirectory(src, dest) {
  fs.mkdirSync(dest, { recursive: true });

  const entries = fs.readdirSync(src, { withFileTypes: true });

  entries.forEach(entry => {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDirectory(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  });
}

console.log('[Build] Complete! Run "npm run build" to package.');

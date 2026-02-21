import { mkdirSync, rmSync, copyFileSync, readdirSync, statSync, readFileSync, writeFileSync } from 'fs';
import { join, resolve } from 'path';
import { fileURLToPath } from 'url';

function copyRecursive(src, dest) {
  const stat = statSync(src);
  if (stat.isDirectory()) {
    try { mkdirSync(dest, { recursive: true }); } catch (e) {}
    for (const entry of readdirSync(src)) {
      copyRecursive(join(src, entry), join(dest, entry));
    }
  } else {
    copyFileSync(src, dest);
  }
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = resolve(__filename, '..');
const root = resolve(__dirname, '..');
const buildDir = join(root, 'build');
const buildAssets = join(buildDir, 'assets');
const projectRoot = resolve(__dirname, '..', '..');
const staticAssets = join(projectRoot, 'static', 'assets');
const templatesDir = join(projectRoot, 'templates');
const targetIndex = join(templatesDir, 'index.html');

try {
  // Clean target assets folder
  rmSync(staticAssets, { recursive: true, force: true });
} catch (e) {}

// Copy assets
copyRecursive(buildAssets, staticAssets);

// Copy index.html -> templates/index.html (Django static template)
try { mkdirSync(templatesDir, { recursive: true }); } catch (e) {}
const sourceIndex = readFileSync(join(buildDir, 'index.html'), 'utf8');
let djangoIndex = sourceIndex;
if (!djangoIndex.startsWith('{% load static %}')) {
  djangoIndex = `{% load static %}\n${djangoIndex}`;
}
djangoIndex = djangoIndex
  .replace(/src="\/static\/assets\/index\.js"/g, 'src="{% static \'assets/index.js\' %}"')
  .replace(/href="\/static\/assets\/index\.css"/g, 'href="{% static \'assets/index.css\' %}"');
writeFileSync(targetIndex, djangoIndex, 'utf8');

console.log('Copied build assets to', staticAssets);
console.log('Copied index.html to', targetIndex);

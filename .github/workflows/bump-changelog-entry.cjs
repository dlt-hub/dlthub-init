'use strict';

// Installed by the engineering agent loop. Edit it in dlt-hub/engineering-agent-loop, not
// here. Writes a dependency bump's changelog entry from the two `uv.lock` files before and
// after the recipe ran, as a draft the reviewing pass then holds to the diff.

const fs = require('node:fs');

// not a TOML parser: every package is a `[[package]]` table whose first two keys are `name`
// and `version`, and a parser would be a dependency in a file that must have none
function parseLock(text) {
  const versions = new Map();
  let name = null;
  for (const line of String(text || '').split('\n')) {
    if (line.trim() === '[[package]]') { name = null; continue; }
    // `dependencies` and `wheels` are arrays of tables with `name` keys of their own
    if (/^\[/.test(line)) { name = null; continue; }
    const n = /^name = "([^"]+)"$/.exec(line);
    if (n) { name = normalise(n[1]); continue; }
    const v = /^version = "([^"]+)"$/.exec(line);
    if (v && name) { versions.set(name, v[1]); name = null; }
  }
  return versions;
}

/** PEP 503: lowercase, and every run of `-`, `_` or `.` is one `-`. */
function normalise(name) {
  return String(name).toLowerCase().replace(/[-_.]+/g, '-');
}

function diffLocks(before, after) {
  const moved = [];
  const added = [];
  const removed = [];
  for (const [name, to] of after) {
    const from = before.get(name);
    if (from === undefined) added.push({ name, to });
    else if (from !== to) moved.push({ name, from, to });
  }
  for (const [name, from] of before) {
    if (!after.has(name)) removed.push({ name, from });
  }
  const byName = (a, b) => a.name.localeCompare(b.name);
  return { moved: moved.sort(byName), added: added.sort(byName), removed: removed.sort(byName) };
}

// the optional groups count too: the root project puts `mypy` and `ruff` in `dev`.
// Line by line, because a `[` inside `authors = [` is indistinguishable from a table
// header to anything matching across lines
function directNames(text, into = new Set()) {
  const names = into;
  let table = '';
  let collecting = false;
  for (const line of String(text || '').split('\n')) {
    if (collecting) {
      if (/^\]/.test(line)) { collecting = false; continue; }
      addSpecifiers(names, line);
      continue;
    }
    const header = /^\[\[?([^\]]+)\]\]?\s*$/.exec(line);
    if (header) { table = header[1]; continue; }
    const key = /^([A-Za-z0-9._-]+)\s*=\s*\[(.*)$/.exec(line);
    if (!key) continue;
    const wanted = (table === 'project' && key[1] === 'dependencies')
      || table === 'project.optional-dependencies';
    if (!wanted) continue;
    if (key[2].includes(']')) addSpecifiers(names, key[2]);
    else { addSpecifiers(names, key[2]); collecting = true; }
  }
  return names;
}

function addSpecifiers(into, line) {
  for (const m of line.matchAll(/"([^"]+)"/g)) {
    const name = /^\s*([A-Za-z0-9][A-Za-z0-9._-]*)/.exec(m[1]);
    if (!name) continue;
    const key = normalise(name[1]);
    if (into instanceof Map) into.set(key, m[1].trim());
    else into.add(key);
  }
}

function directSpecs(text) {
  return directNames(text, new Map());
}

const versions = (list) => list.map((p) => `\`${p.name}\` ${p.from} → ${p.to}`);

// direct dependencies carry both versions and transitives are counted, which is the shape
// of every released entry
function lockBullet({ what, diff, direct }) {
  const isDirect = (p) => direct.has(p.name);
  const named = diff.moved.filter(isDirect);
  const rest = diff.moved.length - named.length;
  const parts = [`Refreshed ${what} to the latest within-constraint versions`];
  if (named.length) parts.push(` (${versions(named).join(', ')})`);
  const tail = [];
  if (rest) tail.push(`${rest} transitive update${rest === 1 ? '' : 's'}`);
  if (diff.added.length) {
    tail.push(`added ${diff.added.map((p) => `\`${p.name}\` ${p.to}`).join(', ')}`);
  }
  if (diff.removed.length) {
    tail.push(`dropped ${diff.removed.map((p) => `\`${p.name}\``).join(', ')}`);
  }
  if (tail.length) parts.push(`, plus ${tail.join(', ')}`);
  return `- ${parts.join('')}.`;
}

function renderEntry({ scaffold, root, direct, rootDirect = null, deps = null, skills = null }) {
  const bullets = [];
  if (scaffold && scaffold.moved.length + scaffold.added.length + scaffold.removed.length) {
    bullets.push(lockBullet({
      what: 'the bundled minimal workspace `uv.lock`', diff: scaffold, direct,
    }));
  }
  if (deps && deps.added.length + deps.removed.length + deps.raised.length) {
    const said = [];
    if (deps.added.length) said.push(`added ${deps.added.map((n) => `\`${n}\``).join(', ')}`);
    if (deps.raised.length) {
      said.push(`changed ${deps.raised.map((r) => `\`${r.name}\` to \`${r.to}\``).join(', ')}`);
    }
    if (deps.removed.length) said.push(`dropped ${deps.removed.map((n) => `\`${n}\``).join(', ')}`);
    bullets.push("- Synced the bundled minimal workspace dependencies with dlt's "
      + `\`workspace_deps()\`: ${said.join(', ')}.`);
  }
  if (root && root.moved.length + root.added.length + root.removed.length) {
    bullets.push(lockBullet({ what: 'the root `uv.lock`', diff: root, direct: rootDirect || direct }));
  }
  if (skills && skills.from !== skills.to) {
    bullets.push(`- Refreshed the bundled skills to workbench \`${skills.to}\`.`);
  }
  return bullets;
}

// appended to an existing `### Changed` block, so a second bump opens no second heading.
// Every released heading below is what the next release moves, and that is a person's act
function insertEntry(changelog, bullets) {
  if (!bullets.length) return changelog;
  const lines = String(changelog).split('\n');
  const at = lines.findIndex((l) => /^## \[Unreleased\]/.test(l));
  if (at === -1) throw new Error('the changelog has no `## [Unreleased]` heading');
  const nextHeading = lines.findIndex((l, i) => i > at && /^## /.test(l));
  const end = nextHeading === -1 ? lines.length : nextHeading;
  const changed = lines.findIndex((l, i) => i > at && i < end && /^### Changed\s*$/.test(l));
  if (changed !== -1) {
    let last = changed;
    for (let i = changed + 1; i < end; i += 1) if (lines[i].trim()) last = i;
    lines.splice(last + 1, 0, ...bullets);
    return lines.join('\n');
  }
  lines.splice(at + 1, 0, '', '### Changed', ...bullets);
  return lines.join('\n');
}

const read = (file) => (file && fs.existsSync(file) ? fs.readFileSync(file, 'utf8') : '');

function main(argv, io = console) {
  const value = (name) => {
    const i = argv.indexOf(name);
    return i === -1 ? null : argv[i + 1];
  };
  const lockDiff = (before, after) => (before && after
    ? diffLocks(parseLock(read(before)), parseLock(read(after)))
    : null);

  const direct = directNames(read(value('--direct')));
  const depsBefore = value('--deps-before');
  const depsAfter = value('--deps-after');
  let deps = null;
  if (depsBefore && depsAfter) {
    const was = directSpecs(read(depsBefore));
    const now = directSpecs(read(depsAfter));
    deps = {
      added: [...now.keys()].filter((n) => !was.has(n)).sort(),
      removed: [...was.keys()].filter((n) => !now.has(n)).sort(),
      raised: [...now.keys()].filter((n) => was.has(n) && was.get(n) !== now.get(n))
        .sort().map((name) => ({ name, from: was.get(name), to: now.get(name) })),
    };
  }
  const skillsFrom = value('--skills-before');
  const skillsTo = value('--skills-after');

  const bullets = renderEntry({
    scaffold: lockDiff(value('--scaffold-before'), value('--scaffold-after')),
    root: lockDiff(value('--root-before'), value('--root-after')),
    direct,
    rootDirect: value('--root-direct') ? directNames(read(value('--root-direct'))) : null,
    deps,
    skills: skillsFrom && skillsTo ? { from: skillsFrom, to: skillsTo } : null,
  });

  if (!bullets.length) {
    io.error('bump-changelog-entry: nothing moved, so there is no entry to write');
    return 1;
  }

  const changelog = value('--changelog');
  if (changelog) {
    fs.writeFileSync(changelog, insertEntry(fs.readFileSync(changelog, 'utf8'), bullets));
    io.error(`bump-changelog-entry: wrote ${bullets.length} bullet(s) into ${changelog}`);
  }
  io.log(bullets.join('\n'));
  return 0;
}

if (require.main === module) process.exit(main(process.argv.slice(2)));

module.exports = {
  parseLock, normalise, diffLocks, directNames, directSpecs, lockBullet, renderEntry,
  insertEntry, main,
};

'use strict';

// Installed here by the engineering agent loop. Writes the changelog entry a dependency bump
// gets, from the two `uv.lock` files before and after the recipe ran. No model is called and
// no secret is read.
//
// Written by a deployment from dlt-hub/engineering-agent-loop; edit it there, not here.
//
// It is deliberately a draft rather than an answer. The reviewing pass that reads the bump is
// handed the locks' summary and this entry, and dimension 3 of the profile's review-diff skill
// is what holds the entry to the diff — so what this has to get right is naming every direct
// dependency that moved, and what it may leave rough is the prose around them.
//
// Dependency-free, and run by `bump-<target>.yml` beside it rather than by any stage: the
// agent has no shell, so nothing a model does reaches this file.

const fs = require('node:fs');

/**
 * name -> version, off a `uv.lock`.
 *
 * `uv.lock` is TOML and this is not a TOML parser. Every package in it is a `[[package]]`
 * table whose first two keys are `name` and `version`, both bare double-quoted strings, and
 * reading those two lines is the whole of what an entry needs. A real parser would be a
 * dependency in a file that must have none, and would answer the same question.
 */
function parseLock(text) {
  const versions = new Map();
  let name = null;
  for (const line of String(text || '').split('\n')) {
    if (line.trim() === '[[package]]') { name = null; continue; }
    // A nested table ends the package's own key block; `dependencies` and `wheels` are arrays
    // of tables and carry `name` keys of their own, which would otherwise overwrite this one.
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

/** What moved between two locks, each list sorted by name. */
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

/**
 * The names a `pyproject.toml` depends on directly.
 *
 * `[project].dependencies` and every group under `[project.optional-dependencies]`, because
 * the root project puts `mypy` and `ruff` in a `dev` group and the released entries name
 * those when they move. The scaffold has no optional group, so for it this is the one list.
 *
 * Read line by line rather than by one expression over the file: a `[` inside `authors = [`
 * or `classifiers = [` is indistinguishable from a table header to anything matching across
 * lines, and that read `[project].dependencies` as belonging to no table at all.
 *
 * A specifier is PEP 508, so the name runs to the first character that cannot be in one.
 */
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
    // `key = ["a", "b"]` on one line, or the opening of a multi-line list.
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

/** The same list as its specifiers, which is what says a constraint was raised. */
function directSpecs(text) {
  return directNames(text, new Map());
}

const versions = (list) => list.map((p) => `\`${p.name}\` ${p.from} → ${p.to}`);

/**
 * One bullet for a lock that moved.
 *
 * Direct dependencies are named with both versions and transitives are counted, which is the
 * shape of every released entry in the file. Naming all of them would be three hundred
 * packages, and the released entries say "plus transitive updates" instead.
 */
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

/** The `### Changed` bullets, in the order the released entries put them. */
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
      + `\`WORKSPACE_DEPS\`: ${said.join(', ')}.`);
  }
  if (root && root.moved.length + root.added.length + root.removed.length) {
    bullets.push(lockBullet({ what: 'the root `uv.lock`', diff: root, direct: rootDirect || direct }));
  }
  if (skills && skills.from !== skills.to) {
    bullets.push(`- Refreshed the bundled skills to workbench \`${skills.to}\`.`);
  }
  return bullets;
}

/**
 * The file with `bullets` under `## [Unreleased]`, in a `### Changed` block.
 *
 * Appended to the block where there is one, so a bump opened while another is still unmerged
 * does not write a second heading. Every released heading below is untouched: that block is
 * what the next release moves under a version, and the release is a person's act.
 */
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

# Usage

Embed the card in any GitHub profile README:

```md
![neofetch card](https://neofetch-readme.vercel.app/api/svg?user=tomas&host=github&os=Arch+Linux&school=FIT+CTU&city=Prague&frontend=React%2C+TypeScript&backend=Node.js%2C+PHP&mail=you%40example.com&icons=javascript,typescript,react,nodedotjs,php,python,git,linux)
```

Every value is read from the URL at request time (nothing is stored) -
change the query string, the card changes, exactly like
[readme-typing-svg](https://readme-typing-svg.demolab.com).

`/svg` is a short alias for `/api/svg` and accepts the same parameters.

## Parameters

All parameters are optional. Omitted lines are simply not shown.

| Param | Default | Notes |
|---|---|---|
| `user` | `guest` | Shown as `user@host` |
| `host` | `github` | Shown as `user@host` |
| `os` | — | Right-panel line |
| `school` | — | Right-panel line |
| `city` | — | Right-panel line |
| `frontend` | — | Right-panel line |
| `backend` | — | Right-panel line |
| `web` | — | Right-panel line |
| `ai` | — | Right-panel line |
| `mobile` | — | Right-panel line |
| `database` | — | Right-panel line |
| `cloud` | — | Right-panel line |
| `devops` | — | Right-panel line |
| `editor` | — | Right-panel line |
| `shell` | — | Right-panel line |
| `terminal` | — | Right-panel line |
| `languages` | — | Right-panel line (spoken languages) |
| `projects` | — | Right-panel line |
| `mail` | — | Right-panel line |
| `github` | — | Right-panel line |
| `linkedin` | — | Right-panel line |
| `website` | — | Right-panel line |
| `status` | — | Right-panel line |
| `hobby` | — | Right-panel line |
| `extra` | — | Extra custom lines: `Label:Value\|Label2:Value2` (max 6, after the fields above) |
| `icons` | `javascript,typescript,react,nodedotjs,php,python,git,linux` | Comma-separated, max 12. Sets both which logos show and their animation order. |
| `speed` | `3` | Seconds each logo holds fully formed, 1–8 |
| `bg` | `#0d0d11` | Card background, hex |
| `border` | `#2a2a33` | Border / rule color, hex |
| `accent` | `#7dd3fc` | Label / username color, hex |
| `text` | `#e4e4e7` | Value text color, hex |
| `cursor` | `on` | `off` hides the blinking cursor |

A literal `+` in any value is treated as a space (standard query-string
convention) - use `%2B` if you actually need a `+` character.

Right-panel values are capped at 42 characters (longer ones are truncated
with `…`); at most 14 lines total (predefined + `extra` combined) are
shown so the layout never overflows the card.

## Available icons

Any of these slugs can be used in `icons`:

```
javascript, typescript, react, vuedotjs, angular, svelte, nodedotjs, php,
python, openjdk, kotlin, swift, go, rust, cplusplus, html5, css3,
tailwindcss, docker, kubernetes, git, github, linux, apple, postgresql,
mysql, mongodb, redis, graphql, amazonwebservices, googlecloud, vercel,
dotnet, lua, bootstrap, blender
```

To add a new icon: add its Simple Icons slug/title/hex to `ICON_CATALOG`
in `tools/neofetch_anim.py`, then regenerate the manifest:

```sh
pip install playwright pillow
python -m playwright install chromium
python tools/neofetch_anim.py
```

This re-renders `generated/icon-frames.json` for the **entire** catalog
(so the live API can keep serving every existing slug). Commit the
updated file - the API never renders images at request time.

## Local preview

```sh
node tools/preview.js -- user=tomas&school=FIT&icons=javascript,react,python
```

Writes `.preview.svg` using the exact same `lib/buildSvg.js` code the
deployed function runs. Open it in a browser to see the live animation
(GitHub-hosted viewing requires SMIL support, same as any browser).

Or run the real function locally with the Vercel CLI:

```sh
vercel dev
# then open http://localhost:3000/api/svg?user=tomas&...
```

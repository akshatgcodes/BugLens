# PRD: BugLens

## Problem

Getting a second pair of eyes on code is slow, and the cheap options are each half an answer. Linters are fast and predictable but only know patterns; asking a chatbot finds subtler bugs but is slow, repeats itself, and hands back a rewritten file you have to diff by hand.

## Goal

One page where pasted code gets both: instant, deterministic checks for the well-known mistakes, then a model review focused on what those checks can't see, with every suggested change shown as a reviewable diff.

## Users

- A developer who wants a quick review of a function or file before opening a PR
- A learner who wants to know *why* something is a bug, not just that a linter complains
- An interviewer or reviewer demonstrating common vulnerabilities with the samples

## User stories

| As a… | I want to… | So that… |
|---|---|---|
| developer | paste code or open a file and get results immediately | I don't wait for a model to tell me about a hardcoded password |
| developer | see AI findings appear while they're written | a slow review still feels responsive |
| developer | know whether an issue came from a rule or the model | I can judge how much to trust it |
| developer | filter by severity | I fix critical issues first |
| developer | see each fix as a before/after and the whole file as a diff | I can review the change instead of trusting it |
| developer | copy the fixed code | I can apply it in my editor |
| developer | reopen past reviews | I can come back to one later |
| developer | use it without an API key | the rules still help when the model isn't available |

## Requirements

- Languages: Python, JavaScript, TypeScript, Java, Go, PHP, plus generic rules for anything else
- Static rules run before any model call and their results are sent first
- Rules ignore matches inside strings and comments unless the rule is about strings or comments
- Model output is streamed, validated per issue, de-duplicated against rule findings, and capped
- Fixes are applied only when they match the code unambiguously; nothing is executed
- Reviews (code, issues, fixed code) are saved and can be listed, opened and deleted
- Owner password login; works with the AI review turned off or unconfigured
- Size limit per review (40,000 characters by default)

## Non-goals

- Running, compiling or importing the submitted code
- Whole-repository analysis or a GitHub integration
- Data-flow analysis across files (the rules are per-line patterns)
- Multiple users or teams

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>

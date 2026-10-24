# Setup guide: API key, paper access, arXiv endorsement

*2026-10-18. Facts marked (verified) come from searches this session; anything else is stated as uncertain.*

---

## A0. Using your Gemini key instead (decided 2026-10-19)
Tier 2 now runs on a **Gemini** model, so no Claude Console account is needed. `generativelanguage.googleapis.com`
is already reachable from this environment.
1. The key that was pasted into the chat must be treated as **exposed**. In Google AI Studio (API keys page),
   **delete that key and create a new one**.
2. Put the **new** key in the environment: title-bar environment menu → **Edit** → add an environment variable
   named exactly **`RAGMV_GEMINI_API_KEY`**. Never paste it in chat or any file.
3. Start a new session in the same environment and confirm the `RAGMV_GEMINI_API_KEY` environment variable is set, then resume using the current experiment instructions in `experiments/E2_generation/`.
4. On the free tier, the 1,600 calls take a few days (daily request limits). Runs resume automatically. Your prompts
   are public benchmark text, so nothing confidential is sent.

## A. The Claude API key (alternative; no longer needed)

### Do you need a separate subscription?
- **Yes, a separate *billing account*, not a new chat subscription.** Your Claude chat plan (Pro/Max) and the Claude
  **API** are billed separately. The API uses **prepaid credits** bought in the **Claude Console**, under Settings →
  Billing (verified, Anthropic support article + secondary sources).
- Some blogs say Max plans include a monthly API credit. **I could not confirm this from Anthropic's own pages.**
  Check your Console's billing page before buying anything.
- **Expected cost:** Tier 2 with Claude Haiku 5.5 is estimated at about **$2** (batch pricing). Sonnet 5.5 as well
  would add about $44. You may have to buy the Console's minimum credit amount, which I could not verify.

### Is it worth it?
It answers the reviewer question "do retrieval differences change the *answers*?". **It is not required for the
preprint.** The retrieval result stands on its own, and without Tier 2 we state this as a limitation. If money is
tight, skip it.

### Steps (only if you decide yes)
1. In a browser, open the **Claude Console** (`console.anthropic.com`; it may redirect to `platform.claude.com`) and sign in.
2. **Settings → Billing**: add the smallest credit amount offered. **Leave auto-reload off.**
3. If you see **Limits** / spend limits, set a low monthly cap (e.g., $10).
4. **API keys → Create key**, name it `ragmv-tier2`, and copy it. It is shown only once.
5. In **this Claude Code environment**: open the cloud environment menu in the session's title bar → **Edit** →
   add an **environment variable** named exactly **`RAGMV_ANTHROPIC_API_KEY`** with the key as its value, and save.
   - Use this name, **not** `ANTHROPIC_API_KEY`, so it cannot interfere with how Claude Code itself is signed in or billed.
   - **Never paste the key into the chat.**
6. **Start a new session in the same environment** (new sessions pick up new variables) and verify the key is available in the new session, then follow the relevant instructions in `experiments/E2_generation/`.
7. After Tier 2, **revoke the key** in the Console.

---

## B. Getting the papers' full texts to me (pick one)

### Option 1 — allow the scholarly sites (best: I can read and verify everything myself)
1. Open the cloud environment menu in the session's title bar → **Edit** → **Network access**.
2. Choose the **Limited** level; **Allowed domains** appears there. In an older app version it is under **Custom**, with
   a box to include the default package managers. Steps: https://code.claude.com/docs/en/cloud-environments#network-access
3. Type **one bare domain per line — no quotes, no commas** (the field rejects `"arxiv.org",`):
   ```
   arxiv.org
   *.arxiv.org
   aclanthology.org
   api.semanticscholar.org
   openreview.net
   huggingface.co
   *.huggingface.co
   *.hf.co
   ```
   Note it is `huggingface.co`, **not** `huggingface.com`. **Keep "Allow package managers" ticked.** Save.
4. Start a new session from the same environment and resume by reviewing the current project instructions and the relevant experiment directory.
   - If you cannot see this menu on your phone, try `claude.ai/code` in a desktop browser.

### Option 2 — a private GitHub repository of PDFs (works with today's settings)
1. On github.com: **New repository** → name `research-papers` → **Private** → Create.
2. Download the PDFs in `literature/protocol_audit/candidates.csv`, **priority 1 first** (5 papers). For an arXiv link,
   change `/abs/` to `/pdf/` (e.g., `https://arxiv.org/pdf/2602.16974`). For the ACL Anthology link, use the PDF
   button on the page.
3. In the new repo: **Add file → Upload files** → drag the PDFs → **Commit changes**.
4. Tell me *"papers are in swaroopchandrashekar13/research-papers"*. I will attach it to the session (you may be
   asked to approve access) and read them.
   - The PDFs stay in the private repo and never enter the public one (copyright).

---

## C. arXiv endorsement — the plan (you asked me to decide)

**Category:** `cs.IR` (Information Retrieval), cross-listed to `cs.CL`.

**Why you need an endorser:** first-time submitters must be endorsed by an established arXiv author in the same
area. Since January 2026 an institutional email alone no longer qualifies (verified, arXiv blog). arXiv advises
asking someone **who knows you personally** and works in the area.

**Plan**
1. **This week:** ask **one** faculty member from your M.Eng programme who knows your capstone work and has arXiv
   papers in computer science. To check whether someone can endorse, open one of their arXiv abstract pages and use
   the link showing which authors are endorsers.
2. **Late November**, when the PDF is final: start the arXiv submission. arXiv emails you a personal endorsement
   request link. Forward it with the note below.
3. **Fallback by 25 Nov** if nobody can endorse: publish a **technical report** as a GitHub release of this repository
   (PDF + code + data manifest). It is public, timestamped and citable in applications. Optionally add a DOI through
   Zenodo's GitHub integration (check Zenodo's current instructions). Submit to arXiv as soon as an endorsement arrives.
4. Do **not** mass-email strangers. If step 1 fails, at most one or two authors of papers we cite, with the finished
   preprint attached.

### Email draft (edit it into your own words before sending)
> **Subject:** Request for arXiv endorsement (cs.IR) — preprint on evaluating chunking in retrieval-augmented generation
>
> Dear Prof. ⟨name⟩,
>
> I hope you are well. I completed the M.Eng in AI & ML at MAHE in 2026 (⟨capstone project title⟩). Since then I have
> carried out an independent study on how evaluation protocols affect conclusions about document chunking in
> retrieval-augmented generation. It was pre-registered, with the code and per-query results public at ⟨repo link⟩.
>
> I would like to post the preprint to arXiv in cs.IR. As a first-time submitter I need an endorsement from an
> established author in the area. Would you be willing to look at the attached draft and, if you consider it
> appropriate for arXiv, endorse it? The endorsement link from arXiv is: ⟨link⟩.
>
> I fully understand if you are unable to; thank you for considering it either way.
>
> Kind regards,
> Swaroop Chand J C

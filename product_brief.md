# UVTS Product Brief

**Product name:** UVTS (User-View Testing System)
**Version:** First release
**Audience:** Non-technical writers and people who review product manuals
**Last updated:** 2026-08-26

## Product Idea

UVTS helps writers find information that may be missing from a product or software manual.

A writer adds a product image, a short product description, and a question count. UVTS uses that product context to create realistic questions. After the writer confirms the questions, they upload a PDF manual and UVTS checks whether the information needed for those questions exists in it. The report shows what is covered, partly covered, or missing.

UVTS does not generate answers to the questions. It only checks whether the manual contains the required information.

## The Problem

Writers often review a manual by checking whether every planned section has been written. Real users think differently. They ask questions based on their goals, experience, and problems.

Information may be missing, incomplete, or spread across different sections. UVTS helps writers find these gaps before the manual is published or users need to contact support.

## Main Users

- Content and manual writers
- Product owners
- Customer support managers
- Quality reviewers

Users do not need technical or AI knowledge.

## Main User Journey

The application guides the writer through five stages in one workspace. It shows the
current stage and lets the writer return to completed stages:

1. Save a product image, product description, and question count.
2. Generate, edit, add, review, and confirm the questions used by UVTS.
3. Upload and validate a PDF manual.
4. Evaluate the confirmed questions against the manual.
5. Read the report and improve the manual.

## Core Features

### 1. Product and Question Setup

The writer provides:

- **Product image:** One private image file of up to 10 MB
- **Product description:** A non-empty explanation of the product and its purpose
- **Question count:** Between 1 and 15 questions, with a suggested starting count of 9

Question types, topics, viewpoints, and per-type splits are deferred until after the basic workflow is validated.

### 2. User-Question Generation and Confirmation

- UVTS creates realistic questions from the product image and description.
- The manual is not required and is never included in question-generation input.
- Questions must be clear, relevant, and different from each other.
- Before confirmation, the writer can edit generated questions, add a question
  manually or with an AI suggestion, or generate a new set.
- The writer explicitly confirms the final questions.
- Confirmed questions cannot change silently after the manual is uploaded.

### 3. Document Box

- Upload one readable PDF manual.
- The manual can contain between 1 and 20 pages.
- Password-protected and image-only scanned PDFs are not supported.
- UVTS shows clear messages when a file cannot be used.

### 4. Automated Testing

For each question, UVTS:

- Identifies the information that the question requires.
- Checks whether that information exists in the manual.
- Shows whether the information was found, partly found, or not found.
- Shows the manual pages containing supporting information.

UVTS does not use outside knowledge and does not write an answer to the question.

### 5. Basic Report

The report shows:

- A clear summary, such as **“7 questions are covered out of 10 total questions.”**
- The number of questions partly covered and not covered.
- Results for every question with supporting page references.
- The most important information gaps.
- Recommendations for improving the manual.
- Suggested questions for a follow-up test.

Only questions for which all important information was found count as covered.

## Result Meanings

- **Information found:** All important information needed for the question exists in the manual.
- **Information partly found:** Some information exists, but an important detail, condition, or step is missing.
- **Information not found:** The manual does not contain relevant information for the question.

These results only measure whether information exists. They do not confirm that the information is correct, clearly written, or safe.

## First-Release Limits

- One manual per test
- A maximum of 20 pages
- A maximum of 15 questions
- One product image of up to 10 MB
- PDF files only
- No scanned or image-only PDFs
- No report downloads
- No comparison between manual versions
- No team comments or approval process

## Privacy and Ease of Use

- Anonymous sessions restrict tests, manuals, and reports to the browser session that
  created them.
- Writers can remove a manual and its connected evaluation and report data.
- Manual contents are sent through the configured OpenRouter models for evaluation.
  A deployment must choose provider data controls that match its privacy policy.
- The first release does not yet define an automatic retention period.
- Instructions, errors, and reports must use plain language.
- Main actions must work with a keyboard and must not depend on color alone.

## How We Will Know It Works

The first release is successful when:

- A writer can go from uploading a manual to reading a report without technical help.
- UVTS saves the product context and creates the requested number of questions.
- Every result correctly shows whether information is found, partly found, or not found.
- Results that find information include real page references.
- The report clearly identifies useful improvements to the manual.

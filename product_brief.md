# UVTS Product Brief

**Product name:** UVTS (User-View Testing Stimulation)  
**Version:** First release  
**Audience:** Non-technical writers and people who review product manuals  
**Last updated:** 2026-08-23  

## Product Idea

UVTS helps writers find information that may be missing from a product or software manual.

A writer uploads a PDF manual. UVTS creates realistic questions from different user viewpoints and checks whether the information needed for those questions exists in the manual. It then produces a simple report showing what is covered, partly covered, or missing.

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

The complete workflow stays on one page:

1. Upload a PDF manual.
2. Generate questions with the suggested or adjusted settings.
3. Review the questions created by UVTS.
4. Evaluate the reviewed questions against the manual.
5. Read the report below the evaluation and improve the manual.

## Core Features

### 1. Document Box

- Upload one readable PDF manual.
- The manual can contain between 1 and 20 pages.
- Password-protected and image-only scanned PDFs are not supported.
- UVTS shows clear messages when a file cannot be used.

### 2. Test Configuration

The writer can select:

- **Question types:** Basic, Cross-paragraph, and Edge-case
- **Topics:** Setup, main tasks, settings, troubleshooting, limitations, safety, privacy, and data handling
- **User viewpoints:** Beginner, Regular user, and Advanced user
- **Question count:** Between 1 and 15 questions

The suggested starting setup is 9 questions, with 3 questions of each type.

### 3. User-Question Generation

- UVTS creates realistic questions based on the manual and selected settings.
- Every question has a type, topic, and user viewpoint.
- Questions must be clear, relevant, and different from each other.
- The writer can generate a new question set before starting the test.

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
- PDF files only
- No scanned or image-only PDFs
- No editing of individual generated questions
- No report downloads
- No comparison between manual versions
- No team comments or approval process

## Privacy and Ease of Use

- Manuals and reports must be kept private and protected.
- Writers must be able to delete their manuals and test results.
- Uploaded manuals must not be used to train general AI models without permission.
- Instructions, errors, and reports must use plain language.
- Main actions must work with a keyboard and must not depend on color alone.

## How We Will Know It Works

The first release is successful when:

- A writer can go from uploading a manual to reading a report without technical help.
- UVTS creates the requested number and types of questions.
- Every result correctly shows whether information is found, partly found, or not found.
- Results that find information include real page references.
- The report clearly identifies useful improvements to the manual.

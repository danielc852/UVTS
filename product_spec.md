# UVTS Product Specification

**Product name:** UVTS (User-View Testing Stimulation)  
**Version:** First release  
**Audience:** Non-technical writers, product owners, designers, and development teams  
**Last updated:** 2026-08-23  

## 1. What is UVTS?

UVTS helps a writer check whether a product or software manual contains the information needed for questions that real users may ask.

The writer uploads a PDF manual and chooses the kinds of questions to test. UVTS creates sample user questions, checks whether the needed information exists in the manual, and produces a report. The report shows what information is present, incomplete, or missing.

The first version of UVTS supports:

- One PDF manual at a time
- A manual of up to 20 pages
- Up to 15 questions in one test
- Three main question types
- A basic results report with recommendations and follow-up questions

## 2. Why is this product needed?

Writers usually review a manual by checking whether all planned sections have been written. Users approach a manual differently. They ask questions based on what they want to do, what they already know, and what has gone wrong.

For example, a manual may explain how to turn on automatic backup and explain export formats in another section. It may not clearly answer this user question:

> Can I change the export format after automatic backup has already been turned on?

UVTS helps writers find these gaps before users need to contact support.

## 3. Main Goal

UVTS should help a writer answer one main question:

> Does this manual give different kinds of users enough information to complete their tasks and solve likely problems?

The report should be easy to understand without technical or AI knowledge.

## 4. Who will use UVTS?

The main user is a person who writes or reviews product information but may not have a technical background.

Examples include:

- A content writer preparing a product manual
- A product owner checking whether a manual is ready to publish
- A customer support manager reviewing common user problems
- A quality reviewer checking whether important information is covered

## 5. Typical User Journey

1. The writer uploads a PDF manual.
2. UVTS checks that the file can be used.
3. The writer chooses the types and number of questions.
4. The writer chooses the topics and user viewpoints to include.
5. UVTS creates a set of sample questions.
6. The writer reviews the questions and starts the test.
7. UVTS checks whether the information needed for each question exists in the manual.
8. UVTS creates a report with results and suggested improvements.

## 6. Core Features

### 6.1 Document Box

The Document Box is where the writer uploads the manual.

#### What the writer can do

- Upload one PDF file.
- See the file name and number of pages.
- Remove the file or replace it before starting a test.
- See whether the file is being uploaded, checked, processed, or is ready.

#### File rules

- The file must be a PDF.
- The PDF must contain between 1 and 20 pages.
- The PDF must not be password-protected.
- The PDF must contain readable text.
- Scanned pages that contain only images are not supported in the first version.
- Only one manual can be tested at a time.

#### What happens when there is a problem

UVTS must explain the problem in plain language and tell the writer what to do next.

Examples:

- “Upload a PDF file.”
- “This PDF has 24 pages. UVTS currently supports up to 20 pages.”
- “This PDF is password-protected. Remove the password and upload it again.”
- “UVTS could not read the text in this PDF. Scanned documents are not supported yet.”

#### The feature is complete when

- A suitable PDF can be uploaded and reaches a Ready state.
- A file with more than 20 pages is rejected with a clear message.
- The writer cannot continue until the manual is ready.
- UVTS remembers the page number of each piece of text so it can show evidence later.
- Replacing the manual removes questions and results from the old manual.

### 6.2 Test Configuration

Test Configuration lets the writer decide which questions UVTS should create.

The setup separates three ideas:

- **Question type:** how the question should use the manual
- **Topic:** what the question is about
- **User viewpoint:** the kind of person asking the question

#### Question types

The first version includes three types:

1. **Basic question**
   - Looks for a direct fact or a short set of steps.
   - The answer will normally be found in one part of the manual.
   - Example: “How do I reset my password?”
2. **Cross-paragraph question**
   - Needs information from two or more paragraphs, sections, or pages.
   - Example: “Can I change the export format after turning on automatic backup?”
3. **Edge-case question**
   - Asks about an unusual situation, a limit, a failed step, or an exception.
   - Example: “What should I do if setup stops before my device appears?”

#### Topics

The writer can choose one or more topics that are relevant to the manual:

- Setup and requirements
- Main product tasks
- Settings and customization
- Troubleshooting and recovery
- Limits and unusual situations
- Safety, privacy, and data handling

If a topic does not appear to be relevant, UVTS can make it unavailable and explain why.

#### User viewpoints

The writer can choose one or more viewpoints:

- **Beginner:** does not know the product or its special terms
- **Regular user:** knows the common tasks but may need help with a problem
- **Advanced user:** asks about settings, limits, and less common situations

These viewpoints describe the sample users asking the questions. They are not UVTS account types.

#### Number of questions

- The writer can choose between 1 and 15 questions.
- At least one question type, one topic, and one user viewpoint must be selected.
- The writer can choose how many questions of each type to create.
- The numbers for all question types must add up to the total.
- If the writer does not choose a split, UVTS divides the questions as evenly as possible.

The suggested starting setup is:

- 9 questions in total
- 3 Basic questions
- 3 Cross-paragraph questions
- 3 Edge-case questions
- All relevant topics
- Beginner, Regular user, and Advanced user viewpoints

#### The feature is complete when

- The writer cannot request fewer than 1 or more than 15 questions.
- The writer cannot continue when a required choice is missing.
- A clear summary shows what questions will be created.
- UVTS saves the choices used for each test.

### 6.3 User-Question Generation

UVTS creates realistic questions based on the manual and the writer's choices.

#### Rules for good questions

Each question must:

- Sound like something a real user might ask.
- Have one question type, one topic, and one user viewpoint.
- Stay connected to the product and situations described in the manual.
- Be different from the other questions in the same set.
- Avoid mentioning page numbers or saying “according to the manual.”
- Use clear, natural language.

Basic questions should focus on common needs. Cross-paragraph questions should bring together related information from different parts of the manual. Edge-case questions may ask about reasonable problems that the manual does not fully explain. This is important because the purpose of UVTS is to find missing information, not only to repeat what is already written.

#### Reviewing the questions

Before testing, the writer can:

- Read the complete numbered question list.
- See the type, topic, and viewpoint for every question.
- Replace the whole set by selecting Generate Again.
- Start the test when satisfied with the set.

Generating again replaces the current questions, so UVTS must show a warning first. Questions cannot change after the test starts. This keeps the results connected to the exact questions that were tested.

Editing one question at a time is not included in the first version.

#### The feature is complete when

- UVTS creates the requested number of questions.
- The number of each question type matches the writer's setup.
- Every question shows its type, topic, and viewpoint.
- The set does not contain repeated questions.
- The question set is saved when testing begins.

### 6.4 Automated Testing

UVTS checks whether the manual contains the information needed for each generated question. It does not test whether an AI agent can write a correct answer.

#### How the test works

For each question, UVTS:

1. Lists the main pieces of information the question requires.
2. Searches the manual for each piece of information.
3. Records which information is present, partly present, or missing.
4. Shows the pages where supporting information was found.
5. Gives the question an information-coverage status.

UVTS does not generate an answer to the question. It must not use outside knowledge or an AI agent's own knowledge to fill a gap. If the information is not in the manual, the result must say so.

#### Result status

Each question receives one of three results:

- **Information found:** The manual contains all important information needed for the question.
- **Information partly found:** The manual contains some relevant information, but an important step, condition, or detail is missing or unclear.
- **Information not found:** The manual does not contain relevant information for the question.

These results only show whether the information exists in the manual. They do not judge whether the information is factually correct, clearly written, or safe.

#### Evidence

For an Information found or Information partly found result, UVTS must show:

- The page number where the information was found
- A short text extract or a simple note describing the evidence
- More than one page when the needed information appears in different parts of the manual

If no useful information is found, UVTS must show “No supporting information found.” It must never create a false page reference.

#### Test summary numbers

UVTS shows:

- The main result as a clear sentence: **X questions are covered out of Y total questions.** For example: **7 questions are covered out of 10 total questions.**
- The number of questions where information was partly found
- The number of questions where information was not found
- Results grouped by question type
- Results grouped by topic
- Results grouped by user viewpoint

Only questions marked Information found count toward X. The total is the number of generated questions in the test. The found, partly found, not found, and failed counts must add up to that total.

#### Progress and failure

- The writer sees how many questions have been completed.
- If one question fails to process, UVTS continues with the others.
- Completed results are kept.
- The writer can try failed questions again.
- UVTS clearly marks a report that contains unfinished or failed questions.

#### The feature is complete when

- Every completed question has one information-coverage result.
- Every found or partly found result includes at least one real page reference.
- An Information not found result does not contain invented evidence.
- The summary numbers match the individual results.
- One failed question does not remove the other results.

### 6.5 Basic Report

The Basic Report explains the results and helps the writer decide what to improve.

#### Report contents

The report includes:

1. **Test summary**
   - Manual name and number of pages
   - Test date
   - Number of questions
   - Choices used to create the questions
   - Main result shown as **X questions are covered out of Y total questions.**
   - Counts for Information partly found and Information not found
2. **Coverage overview**
   - Results by question type
   - Results by topic
   - Results by user viewpoint
3. **Question results**
   - The question and its labels
   - Information found, partly found, or not found
   - Information found and information missing
   - Page references
4. **Main gaps**
   - Missing or incomplete information grouped by subject
   - The questions affected by each gap
   - An explanation of why the gap matters
5. **Recommendations**
   - Clear writing changes, such as adding a missing requirement, explaining a term, joining related steps, describing a limit, or adding recovery instructions
6. **Follow-up**
   - Suggested questions to use after the manual is updated
   - A suggestion to run the test again
   - Any failed questions that still need to be tested

#### Recommendation priority

- **High:** Missing information may stop a common task or may affect safety, privacy, or important data.
- **Medium:** Incomplete or scattered information may cause mistakes or support requests.
- **Low:** The information exists but could be easier to find or understand.

Every recommendation must connect to at least one test result. UVTS should recommend improvements to the manual, not changes to the product itself.

#### Report actions

The writer can:

- Read the full report in UVTS.
- Open a result to see its explanation and page evidence.
- Start another test with the same manual and different choices.
- Run the same type of test after updating the manual.

Downloading the report as a PDF or spreadsheet is not part of the first version.

#### The feature is complete when

- The report summary matches the detailed question results.
- The main result uses the sentence **X questions are covered out of Y total questions.**
- The report does not include AI-generated answers to the questions.
- Each main gap links to the questions it affects.
- Each recommendation links to a gap or question.
- Failed or unfinished tests are clearly marked.
- The language is understandable without technical knowledge.

## 7. Main Screens

### New Test

The writer uploads a manual and chooses the test settings.

### Question Review

The writer reviews the generated questions, generates a new set, or starts the test.

### Testing Progress

The writer sees how many questions have been tested and whether any question needs to be tried again.

### Report

The writer sees the overall results first, followed by individual questions, missing information, recommendations, and follow-up work.

## 8. Important Product Rules

1. One test uses one PDF manual.
2. The manual can contain no more than 20 pages.
3. One test can contain no more than 15 questions.
4. Every question has a type, topic, and user viewpoint.
5. Questions do not change after testing starts.
6. The uploaded manual is the only source used to check whether information exists.
7. Any result that says information was found must show a page reference.
8. Results measure whether information exists, not its accuracy or writing quality.
9. Every recommendation must be supported by a test result.
10. Replacing or deleting a manual also removes its unfinished questions and connected results.

## 9. Privacy, Safety, and Ease of Use

- Manuals and reports must be kept private.
- Files and results must be protected while stored and transferred.
- Uploaded manuals must not be used to train general AI models unless the user clearly agrees.
- The writer must be able to delete a manual and its test results.
- The product must explain how long files and reports are kept.
- All main actions must work with a keyboard.
- Results must use words and labels, not color alone.
- Error messages and instructions must use plain language.
- UVTS must clearly explain that its results are suggestions and do not replace legal, safety, or expert review.

## 10. What is Not Included in the First Version?

- Testing more than one manual at the same time
- Manuals longer than 20 pages
- Word documents, websites, videos, or other file types
- Scanned PDFs that need text recognition
- Checking whether statements in the manual are factually correct
- Testing the product interface or watching real users
- Editing individual generated questions
- Comparing two versions of a manual
- Team comments and approval steps
- Downloading reports
- Connections to support, document, or project-management tools

## 11. Risks and How UVTS Should Handle Them

### AI judgment may not match a human judgment

UVTS should show its reasoning in simple terms: what information was needed, what was found, what was missing, and which pages were used. The writer can then judge whether the result makes sense.

### Questions may focus too much on information already in the manual

UVTS should create some realistic edge-case questions that expose missing information. These questions must still relate to the product described in the manual.

### A strong result may create too much confidence

Every report should explain that UVTS checks whether information exists in the manual. A strong result does not prove that the information is correct, safe, complete for every possible user, or easy to follow.

### Some PDFs may be difficult to read

UVTS should reject files with no readable text and clearly explain the problem. Page references let the writer compare each result with the original manual.

### A new test may create different questions

UVTS saves the exact questions used in each test. Questions never change after that test begins.

## 12. How We Will Know the First Version Is Ready

The first version is ready for a small group of users when:

- A suitable 1-to-20-page PDF can complete the full journey from upload to report.
- Unsupported PDFs fail safely and show a useful message.
- The writer can create between 1 and 15 questions using all three question types.
- Every completed result shows an information-coverage status and real page evidence when information is found.
- The report clearly shows missing information and useful recommendations.
- Writers without technical knowledge can understand the setup and report during user testing.
- Human reviewers test a sample group of manuals and agree that most results are reasonable.
- Privacy, deletion, keyboard use, and readable status labels have been tested.

## 13. Possible Future Features

- Support for scanned PDFs
- Longer manuals and more than one manual per test
- Custom question types, topics, and user viewpoints
- Editing or adding individual questions
- Saved test setups
- Comparing old and new versions of a manual
- Downloadable and shareable reports
- Team review and approval tools
- Connections to support-ticket and documentation systems
- Separate checks for readability, consistency, and factual accuracy

## 14. Decisions Still Needed

Before development begins, the team must decide:

- Whether users need an account
- The largest allowed PDF file size
- How long manuals and reports are kept
- Whether a writer can stop a test while it is running
- The expected waiting time for question generation and testing
- How the team will check that UVTS results are accurate enough for release

#!/usr/bin/env python3
"""
restore_3107.py — restores the 31 July 2026 mock exam session (FLK1, 80%, 28/35)
that was never saved to the server, rebuilt from the PDF export.

Run once from Terminal:
    cd "/Users/ghitab/Documents/Claude/Projects/Mission solicitor"
    python3 restore_3107.py

Safe to run twice: the API uses INSERT IGNORE on a unique datetime, and this
script checks first, so a repeat run will not create a duplicate.

Note: for the 7 incorrect answers the PDF did not preserve which option was
selected (the colour highlight is lost when printing), so userOption is blank
for those. Everything else - score, subject breakdown, question text and the
correct answers - is complete.
"""
import json, urllib.request

API = 'https://bidouillecode.dev/solicitor/progress.php'
SESSION = json.loads(r'''
{
 "datetime": "2026-07-31T17:51:00.000Z",
 "paper": "FLK1",
 "percentage": 80.0,
 "correct": 28,
 "totalQ": 35,
 "durationMode": 60,
 "subjects": {
  "Business Law and Practice": {
   "correct": 5,
   "total": 6
  },
  "Contract Law": {
   "correct": 4,
   "total": 5
  },
  "Dispute Resolution": {
   "correct": 5,
   "total": 6
  },
  "Ethics and Professional Conduct": {
   "correct": 5,
   "total": 5
  },
  "Legal Services": {
   "correct": 3,
   "total": 4
  },
  "Legal System": {
   "correct": 2,
   "total": 4
  },
  "Tort": {
   "correct": 4,
   "total": 5
  }
 },
 "questions": [
  {
   "preview": "The deadline for serving a witness statement on",
   "questionText": "The deadline for serving a witness statement on the other party was yesterday. The solicitor has not been able to get a signed copy from the client. The solicitor receives a telephone call from the opposing solicitor, who is furious that the statement was not served on time and who threatens to issue an urgent application to the court. To calm the opposing solicitor down, the solicitor tells them not to worry and that they will serve the statement by 10am tomorrow. Which of the following best explains the solicitorʼs professional conduct position?",
   "subject": "Ethics and Professional Conduct",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "A",
   "correctOption": "A",
   "userAnswer": "The solicitor has given an undertaking which is binding upon the solicitor personally.",
   "correctAnswer": "The solicitor has given an undertaking which is binding upon the solicitor personally."
  },
  {
   "preview": "An owner of a small business and a local supplier are in dispu",
   "questionText": "An owner of a small business and a local supplier are in dispute regarding the cost of goods. The owners have stopped speaking to each other which has had a significant impact on the communications between employees with orders getting missed. Success of the businesses depends on their continued operations. Which of the following would be the most appropriate next step?",
   "subject": "Dispute Resolution",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "C",
   "correctOption": "C",
   "userAnswer": "Mediation",
   "correctAnswer": "Mediation"
  },
  {
   "preview": "A private limited company is a small family-run busine",
   "questionText": "A private limited company is a small family-run business with all of the four shareholders living in the same postcode district. Three of the shareholders each own 30% of shares entitling them to attend and vote at a general meeting. The fourth shareholder owns the remaining 10%. A couple of company matters require an urgent shareholder meeting and they ask your advice on whether they can shorten the notice needed for this meeting. Which of the statements below best describes your advice?",
   "subject": "Business Law and Practice",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": false,
   "userOption": "",
   "correctOption": "A",
   "userAnswer": "",
   "correctAnswer": "A majority in number of members owning not less than 90% of the voting shares need to consent to short notice; so the three shareholders who each own 30% of the shares all need to consent."
  },
  {
   "preview": "A solicitor acts for a client in relation to the acquisition of a privat",
   "questionText": "A solicitor acts for a client in relation to the acquisition of a private limited company. Two days before the transaction is due to complete, the solicitor suspects that the client will be using the transaction to launder money. The solicitor reports this to the nominated officer who makes a suspicious activity report to the relevant authority. What action should the solicitor now take?",
   "subject": "Legal Services",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": false,
   "userOption": "",
   "correctOption": "C",
   "userAnswer": "",
   "correctAnswer": "Proceed with the transaction only after receiving authorisation from the relevant authority."
  },
  {
   "preview": "A solicitor is acting for a client in a litigation matt",
   "questionText": "A solicitor is acting for a client in a litigation matter. At the hearing, the client loses the case and is ordered to pay £5,000 towards the opponentʼs costs. Outside court the solicitor says to their opponent, “Donʼt worry. Iʼll make sure that the £5,000 will be paid within the next 14 days.” Fourteen days have now elapsed, and the client has still not provided the solicitor with any funds to pay the costs. Who can force the solicitor to comply with the promise?",
   "subject": "Ethics and Professional Conduct",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "B",
   "correctOption": "B",
   "userAnswer": "The court.",
   "correctAnswer": "The court."
  },
  {
   "preview": "A joiner, who is a sole trader, entered a verbal contract for the pur",
   "questionText": "A joiner, who is a sole trader, entered a verbal contract for the purchase of second-hand tools from a large tool hire company. There were no specific express terms as to quality. The tools turned out to be faulty. What is the legal position?",
   "subject": "Contract Law",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "A",
   "correctOption": "A",
   "userAnswer": "There will be relevant statutory implied terms that apply to this business-to- business transaction.",
   "correctAnswer": "There will be relevant statutory implied terms that apply to this business-to- business transaction."
  },
  {
   "preview": "A homeowner, who is moving from a house to a flat where they ar",
   "questionText": "A homeowner, who is moving from a house to a flat where they are not allowed pets, agrees to sell their pedigree French bulldog to their neighbour for £100, knowing that the neighbour is very fond of the dog and will give it a good home. However, on the day of the move the homeowner knocks on their neighbourʼs door asking for more money as they found out the dog is worth over £1,000, so £100 is not a fair price. Is there a binding contract?",
   "subject": "Contract Law",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "C",
   "correctOption": "C",
   "userAnswer": "Yes, as consideration only has to be sufficient, not economically adequate.",
   "correctAnswer": "Yes, as consideration only has to be sufficient, not economically adequate."
  },
  {
   "preview": "The Environmental Safety Bill has passed through the House of C",
   "questionText": "The Environmental Safety Bill has passed through the House of Commons and the House of Lords. The Bill has been sent to the Monarch for Royal Assent. The Royal does not support the Bill. Which of the following statements best describes the actions that the Monarch can take?",
   "subject": "Legal System",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "D",
   "correctOption": "D",
   "userAnswer": "The Monarch grants royal assent to all legislation.",
   "correctAnswer": "The Monarch grants royal assent to all legislation."
  },
  {
   "preview": "A customer has tripped on a loose floor tile in a restaurant and has broken",
   "questionText": "A customer has tripped on a loose floor tile in a restaurant and has broken their arm. Expert evidence from a doctor suggests that the customer has a weakened bone structure and would not otherwise have suffered this injury. Will the occupier of the restaurant be held liable for the broken arm?",
   "subject": "Tort",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "B",
   "correctOption": "B",
   "userAnswer": "Yes, because of the eggshell skull rule.",
   "correctAnswer": "Yes, because of the eggshell skull rule."
  },
  {
   "preview": "A gadget enthusiast receives an amateur drone for their birthday. Whilst o",
   "questionText": "A gadget enthusiast receives an amateur drone for their birthday. Whilst operating the drone, it malfunctions and falls from the sky. It lands on concrete, and smashes into several pieces, beyond repair. Can the enthusiast sue the manufacturer in common law negligence?",
   "subject": "Tort",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "E",
   "correctOption": "E",
   "userAnswer": "No, because the enthusiast has not suffered a personal injury or property damage.",
   "correctAnswer": "No, because the enthusiast has not suffered a personal injury or property damage."
  },
  {
   "preview": "A local university student suffers from dyslexia and requires extr",
   "questionText": "A local university student suffers from dyslexia and requires extra time to read exam questions. The university wants advice about their obligations in relation to this student. What steps must the university take to ensure that they do not breach the law?",
   "subject": "Legal Services",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "B",
   "correctOption": "B",
   "userAnswer": "The university needs to make reasonable adjustment to ensure that the student is not disadvantaged in comparison to other students.",
   "correctAnswer": "The university needs to make reasonable adjustment to ensure that the student is not disadvantaged in comparison to other students."
  },
  {
   "preview": "While reviewing a file as part of the firmʼs interna",
   "questionText": "While reviewing a file as part of the firmʼs internal compliance policy, the reviewer believes that a solicitor handling a matter has changed dates on court proceedings and missed court deadlines for directions. The reviewer immediately informs the firmʼs compliance officer for legal practice (COLP). Which of the following depicts what may happen to the solicitor?",
   "subject": "Ethics and Professional Conduct",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "A",
   "correctOption": "A",
   "userAnswer": "The solicitor may face disciplinary action and sanctions from the Solicitors Disciplinary Tribunal (SDT) and the SRA (Solicitors Regulatory Authority).",
   "correctAnswer": "The solicitor may face disciplinary action and sanctions from the Solicitors Disciplinary Tribunal (SDT) and the SRA (Solicitors Regulatory Authority)."
  },
  {
   "preview": "A wife, who is having trouble in their marriage to their husband, a",
   "questionText": "A wife, who is having trouble in their marriage to their husband, agrees to lend their husband £1,000 to go on holiday with friends. The wife is hoping that it will make their husband realise they miss them and it will reignite a spark within the marriage. Sadly, the holiday has the opposite effect, and the husband decides to start divorce proceedings. The wife asks the husband for the £1,000 back. The husband refuses, saying they were still owed a birthday present from the previous year anyway. Is the wife entitled to the money back?",
   "subject": "Contract Law",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "B",
   "correctOption": "B",
   "userAnswer": "No, because they are married there is presumed to be no intention to create legal relations.",
   "correctAnswer": "No, because they are married there is presumed to be no intention to create legal relations."
  },
  {
   "preview": "Entrepreneurs have acquired a private limited compan",
   "questionText": "Entrepreneurs have acquired a private limited company off the shelf from their solicitors. Which one of the following best describes what must happen for them to commence operating their new business?",
   "subject": "Business Law and Practice",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "B",
   "correctOption": "B",
   "userAnswer": "Replace the first director(s) and shareholder(s).",
   "correctAnswer": "Replace the first director(s) and shareholder(s)."
  },
  {
   "preview": "The judge at the Court of Appeal (Civil Division) needs to apply th",
   "questionText": "The judge at the Court of Appeal (Civil Division) needs to apply the Social Services Act 1988. Section 5 of the Act refers to “family”. When applying the literal rule, the judge is faced with an absurd outcome that does not fit the current case.Which is the next step that the judge needs to take?",
   "subject": "Legal System",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": false,
   "userOption": "",
   "correctOption": "A",
   "userAnswer": "",
   "correctAnswer": "The judge should apply the golden rule."
  },
  {
   "preview": "A Member of Parliament (MP) has recently introduced a private m",
   "questionText": "A Member of Parliament (MP) has recently introduced a private memberʼs bill in the House of Commons.What stages does the Bill need to go through to become law?",
   "subject": "Legal System",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": false,
   "userOption": "",
   "correctOption": "D",
   "userAnswer": "",
   "correctAnswer": "The Bill needs to go through three readings and a committee stage at the House of Commons and the House of Lords and then receive the Royal Assent"
  },
  {
   "preview": "Which one of the following best describes who can gr",
   "questionText": "Which one of the following best describes who can grant a floating charge over business assets?",
   "subject": "Business Law and Practice",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "C",
   "correctOption": "C",
   "userAnswer": "Only companies and limited liability partnerships can grant a floating charge.",
   "correctAnswer": "Only companies and limited liability partnerships can grant a floating charge."
  },
  {
   "preview": "During a professional football match, a player performed an exceptionally l",
   "questionText": "During a professional football match, a player performed an exceptionally late tackle on an opposing player. As a result, the opposing player suffered a broken leg. The regulatory body reviewed television footage of the incident after the match. It concluded that the late tackle was a deliberate attack and has issued the offending player with a 12-month ban. What advice would you give to the injured, opposing player about a possible claim in negligence against the offending player?",
   "subject": "Tort",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "C",
   "correctOption": "C",
   "userAnswer": "The nature of the tackle goes beyond the level of any implied consent.",
   "correctAnswer": "The nature of the tackle goes beyond the level of any implied consent."
  },
  {
   "preview": "A department store ordered boxed chocolates to sell in its store. I",
   "questionText": "A department store ordered boxed chocolates to sell in its store. It was listed as a written term of the contract that the chocolates be packaged in the storeʼs own-brand packaging, as the store famously only sells own- branded products. Once delivered it was discovered that the chocolates were instead in packaging representing the manufacturerʼs brand. The manufacturer claims the packaging detail was only a warranty and the store can still sell the goods. The department store says it was obviously a condition and they cannot sell the goods. What is the likely legal position?",
   "subject": "Contract Law",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": false,
   "userOption": "",
   "correctOption": "D",
   "userAnswer": "",
   "correctAnswer": "The clause will be held to be a condition of the contract."
  },
  {
   "preview": "A local council wants to sue a road services company for da",
   "questionText": "A local council wants to sue a road services company for damages for breach of contract. The company failed to complete a project almost 6 years ago and the council had to bring in another contractor and pay extra to have the work completed. The councilʼs solicitors wrote a letter of claim to the company 6 months ago and have just received a response from the companyʼs solicitors in which they suggest a mediation should take place before proceedings are issued. They have proposed dates for a mediation in 2 monthsʼ time. Which of the following statements best describes when the councilʼs breach of contract claim should be issued?",
   "subject": "Dispute Resolution",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "C",
   "correctOption": "C",
   "userAnswer": "The claim must be issued before 6 years from the date of the breach of contract, unless the council and the company agree terms of a standstill agreement that has the effect of extending the limitation deadline.",
   "correctAnswer": "The claim must be issued before 6 years from the date of the breach of contract, unless the council and the company agree terms of a standstill agreement that has the effect of extending the limitation deadline."
  },
  {
   "preview": "A junior associate works at a law firm and is currently on materni",
   "questionText": "A junior associate works at a law firm and is currently on maternity leave. The junior associate receives an email form her employer saying that she is being given a notice of dismissal, as the firm cannot afford to wait for her to come back and that clients are complaining. What claim can the junior associate bring against her employer?",
   "subject": "Legal Services",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "C",
   "correctOption": "C",
   "userAnswer": "The junior associate can bring a claim for direct discrimination as she has been dismissed because of her protected characteristic.",
   "correctAnswer": "The junior associate can bring a claim for direct discrimination as she has been dismissed because of her protected characteristic."
  },
  {
   "preview": "A claimant is in an employment tribunal case on constructive dism",
   "questionText": "A claimant is in an employment tribunal case on constructive dismissal against their employer. When applying Employment Relations Act 2000 s 3, the claimantʼs lawyer refers to Hansard.What does the lawyer want to achieve by referring to Hansard?",
   "subject": "Legal System",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "C",
   "correctOption": "C",
   "userAnswer": "Reference to Hansard is made to see what the intentions of the promoters of the bill were.",
   "correctAnswer": "Reference to Hansard is made to see what the intentions of the promoters of the bill were."
  },
  {
   "preview": "A grandparent purchased a brand-new car for a grandchild. After 18 mont",
   "questionText": "A grandparent purchased a brand-new car for a grandchild. After 18 months, the grandparent paid to replace the rear nearside tyre, because it had a puncture. Unfortunately, the replacement tyre was defective and caused a blowout on the motorway. The grandchildʼs car collided with the centre reservation and was written off. The grandchild was unharmed. Does the grandchild have a claim in negligence against the manufacturer of the tyre?",
   "subject": "Tort",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": false,
   "userOption": "",
   "correctOption": "C",
   "userAnswer": "",
   "correctAnswer": "Yes, but not in respect of the replacement tyre."
  },
  {
   "preview": "A businessman once studied law and wants to provide legal advi",
   "questionText": "A businessman once studied law and wants to provide legal advice to a friend in relation to a contractual dispute. The businessman does not belong to any of the authorised group of persons and has never worked in the legal sector. Would the businessman be allowed to give legal advice?",
   "subject": "Legal Services",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "B",
   "correctOption": "B",
   "userAnswer": "Yes, because legal advice is not a reserved legal activity.",
   "correctAnswer": "Yes, because legal advice is not a reserved legal activity."
  },
  {
   "preview": "A civil claim proceeding to trial in the High Court includes sta",
   "questionText": "A civil claim proceeding to trial in the High Court includes standard directions for expert evidence from separate experts. Each partyʼs expert has finalised their report and the reports have been exchanged. What is the typical next stage of the expertsʼ work?",
   "subject": "Dispute Resolution",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "E",
   "correctOption": "E",
   "userAnswer": "Discussion between the experts.",
   "correctAnswer": "Discussion between the experts."
  },
  {
   "preview": "An ambulance driver, employed by the ambulance service, s",
   "questionText": "An ambulance driver, employed by the ambulance service, suffered serious injuries when they were involved in a collision when driving an ambulance. The collision was the fault of another driver driving dangerously. However, the driverʼs injuries would not have been serious but for a defective seatbelt. The maintenance of the ambulance was outsourced to an independent company with a contract with the ambulance service. Is the ambulance driver likely to have a cause of action against the maintenance company?",
   "subject": "Dispute Resolution",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "A",
   "correctOption": "A",
   "userAnswer": "Yes, because the maintenance company would have a duty of care to a driver of the ambulance they maintain.",
   "correctAnswer": "Yes, because the maintenance company would have a duty of care to a driver of the ambulance they maintain."
  },
  {
   "preview": "The three shareholders of a private limited company h",
   "questionText": "The three shareholders of a private limited company hold 45%, 30% and 25% shares respectively. The company intends to amend its articles by special resolution and is considering whether to use a written resolution or invite the shareholders to a general meeting. Which scenario below would best ensure that, whichever method is used, the special resolution is passed?",
   "subject": "Business Law and Practice",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "E",
   "correctOption": "E",
   "userAnswer": "The three shareholders attend the general meeting and vote in its favour; the shareholders with 45% and 30% shares respectively consent to the written resolution.",
   "correctAnswer": "The three shareholders attend the general meeting and vote in its favour; the shareholders with 45% and 30% shares respectively consent to the written resolution."
  },
  {
   "preview": "A solicitor is the senior partner of a law firm that",
   "questionText": "A solicitor is the senior partner of a law firm that has had its case load taken over by the County Court for management. It has emerged that the firm took on several cases in personal injury, even though their specialism is conveyancing. The firm employs two junior solicitors to handle all personal injury claims. The employees have failed to manage the cases appropriately, missing a number of court deadlines and failing to obtain medical evidence in some cases. They have also made misleading statements to the court and in some cases falsified documents to cover up the fact that documents have not been filed on time. There is a chaotic system of case management and minimal supervision at the firm. Which of the following statements best describes the professional conduct implications for the senior partner in the circumstances?",
   "subject": "Ethics and Professional Conduct",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "B",
   "correctOption": "B",
   "userAnswer": "Although not personally involved in handling the cases, the senior partner has breached professional conduct regulations by failing to supervise the solicitors and the conduct of the cases.",
   "correctAnswer": "Although not personally involved in handling the cases, the senior partner has breached professional conduct regulations by failing to supervise the solicitors and the conduct of the cases."
  },
  {
   "preview": "A first-time church attender was so struck by the message, they",
   "questionText": "A first-time church attender was so struck by the message, they decided to formally join the church as a member. The minister explained that the church asked for a \"faith commitment\" from its members. In addition to giving money, members were expected to work for the church in their homeless hostel and their behaviour was closely controlled. The church attender had an inheritance of £100,000. They decided to give £20,000 to the church immediately and changed their will to leave the rest to the church. The church attender worked for the church until they became ill and were taken home by their parents to recuperate. After several years away from the church, the church attender decided they needed a proper job and a place of their own. They changed their will and asked for their money back. Will the church have to return the money?",
   "subject": "Contract Law",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "E",
   "correctOption": "E",
   "userAnswer": "No, there was presumed influence under a protected relationship. The person's gift was not valid. However, lapse of time means rescission is not possible.",
   "correctAnswer": "No, there was presumed influence under a protected relationship. The person's gift was not valid. However, lapse of time means rescission is not possible."
  },
  {
   "preview": "A company claims it is owed £500,000 from a customer for t",
   "questionText": "A company claims it is owed £500,000 from a customer for the supply of goods. The parties have done business for years. The purchase agreement between the company and the customer has a standard arbitration clause. However, the company has issued a claim in the English court for payment of the debt. Which of the following statements best describes the legal position?",
   "subject": "Dispute Resolution",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "B",
   "correctOption": "B",
   "userAnswer": "The customer can challenge the courtʼs jurisdiction in the acknowledgment of service and then apply to stay the proceedings.",
   "correctAnswer": "The customer can challenge the courtʼs jurisdiction in the acknowledgment of service and then apply to stay the proceedings."
  },
  {
   "preview": "A solicitor works for a large international law firm",
   "questionText": "A solicitor works for a large international law firm in London. The solicitor and colleagues have a social media forum that they use to communicate with each other. The forum covers mainly social interactions. It has emerged that the solicitor and some colleagues on the chat have held a competition to rank female colleagues on the basis of their attractiveness. There are also comments suggesting that a transgender trainee has a “lesbian” haircut. The solicitor and colleagues involved in the chat deny any wrongdoing, by justifying the chat as “harmless banter”. They have apologised for the comments to the respective employees.Which of the following best describes the professional conduct implications in the circumstances?",
   "subject": "Ethics and Professional Conduct",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "A",
   "correctOption": "A",
   "userAnswer": "The solicitor has breached the professional conduct regulations by engaging in sexist and transphobic conduct.",
   "correctAnswer": "The solicitor has breached the professional conduct regulations by engaging in sexist and transphobic conduct."
  },
  {
   "preview": "Two businesspeople are forming a private limited com",
   "questionText": "Two businesspeople are forming a private limited company. They have decided it will adopt the Model Articles for private limited companies in their entirety and without amendment. Which of the following must be supplied to the Registrar of Companies (at Companies House) to complete the registration process?",
   "subject": "Business Law and Practice",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "E",
   "correctOption": "E",
   "userAnswer": "Memorandum and Form IN01",
   "correctAnswer": "Memorandum and Form IN01"
  },
  {
   "preview": "A rally car driver invites a friend to join them in their rally car for a spin a",
   "questionText": "A rally car driver invites a friend to join them in their rally car for a spin around a track on their own private land. The rally car driver has been drinking, and the friend is aware of this. Whilst racing round the track together, the rally car driver takes a turn too quickly. The car flips over, causing the friend to suffer a fractured skull. What advice would you give to the friend?",
   "subject": "Tort",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "E",
   "correctOption": "E",
   "userAnswer": "The driver may escape all liability for negligence, on the grounds that you consented to the risk of harm.",
   "correctAnswer": "The driver may escape all liability for negligence, on the grounds that you consented to the risk of harm."
  },
  {
   "preview": "A business that provides wedding venues has been served with",
   "questionText": "A business that provides wedding venues has been served with a claim form and particulars of claim from a couple who were dissatisfied with the venue for their wedding. The defendant has acknowledged service but the deadline for service of the defence will be impossible for them to meet. There are 18 days left and the claimants have refused to agree any extension of time. What is the correct procedure for the defendant to ext defence?",
   "subject": "Dispute Resolution",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": false,
   "userOption": "",
   "correctOption": "A",
   "userAnswer": "",
   "correctAnswer": "Issue and serve an application for an order to ext a witness statement explaining the reason further time is needed."
  },
  {
   "preview": "A sole trader has decided to incorporate their busines",
   "questionText": "A sole trader has decided to incorporate their business as a private limited company and plans to be the only subscriber to the memorandum of association. Which of the following best describes the proposed new company?",
   "subject": "Business Law and Practice",
   "source": "Restored from PDF export 31/07/2026",
   "isCorrect": true,
   "userOption": "D",
   "correctOption": "D",
   "userAnswer": "The sole trader can be the companyʼs sole director, only shareholder and, if it opts to have one, its company secretary.",
   "correctAnswer": "The sole trader can be the companyʼs sole director, only shareholder and, if it opts to have one, its company secretary."
  }
 ]
}
''')

def get():
    with urllib.request.urlopen(API, timeout=30) as r:
        return json.loads(r.read())

def post(payload):
    req = urllib.request.Request(API, data=json.dumps(payload).encode(),
                                 method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def main():
    print("Checking existing sessions...")
    try:
        existing = get()
    except Exception as e:
        print(f"  ERROR: could not reach the API ({e})")
        print("  Is the site up? Try loading", API, "in a browser.")
        return

    print(f"  {len(existing)} session(s) currently stored")
    if any(s.get('datetime') == SESSION['datetime'] for s in existing):
        print("  The 31 July session is ALREADY stored - nothing to do.")
        return

    print(f"Restoring {SESSION['datetime']} - {SESSION['paper']}, "
          f"{SESSION['percentage']}% ({SESSION['correct']}/{SESSION['totalQ']})...")
    post(SESSION)

    after = get()
    ok = any(s.get('datetime') == SESSION['datetime'] for s in after)
    print(f"  {'OK - restored' if ok else 'FAILED - not found after POST'}. "
          f"{len(after)} session(s) now stored.")
    if ok:
        latest = sorted(after, key=lambda s: s.get('datetime',''))[-1]
        print(f"  Latest session is now {latest['datetime']} "
              f"({latest['percentage']}%)")

if __name__ == '__main__':
    main()

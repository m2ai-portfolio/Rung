# Rung Therapist Onboarding Guide

## Welcome to Rung

Rung is an AI-powered psychology support system designed to enhance your clinical practice. This guide will help you get started with the platform and make the most of its capabilities.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Understanding Rung and Beth](#2-understanding-rung-and-beth)
3. [Client Onboarding](#3-client-onboarding)
4. [Pre-Session Workflow](#4-pre-session-workflow)
5. [Post-Session Workflow](#5-post-session-workflow)
6. [Couples Therapy Features](#6-couples-therapy-features)
7. [Development Plans](#7-development-plans)
8. [Privacy and Security](#8-privacy-and-security)
9. [Best Practices](#9-best-practices)
10. [Getting Support](#10-getting-support)

---

## 1. Getting Started

### 1.1 Account Setup

1. **Receive Invitation Email**
   - You'll receive an email with your login credentials
   - Click the link to set up your account

2. **Set Up Multi-Factor Authentication (MFA)**
   - Download an authenticator app (Google Authenticator, Authy, etc.)
   - Scan the QR code during setup
   - MFA is required for all logins (HIPAA compliance)

3. **Complete Your Profile**
   - Add your practice information
   - Configure notification preferences
   - Review and accept terms of service

### 1.2 First Login

```
1. Go to https://app.rung.health
2. Enter your email and password
3. Enter the 6-digit code from your authenticator app
4. You'll see your therapist dashboard
```

### 1.3 Dashboard Overview

Your dashboard shows:
- **Active Clients**: List of clients enrolled in Rung
- **Pending Sessions**: Upcoming sessions with pre-session briefs
- **Recent Activity**: Latest analyses and client guides
- **Couples Links**: Active couples therapy relationships

---

## 2. Understanding Rung and Beth

### 2.1 What is Rung?

**Rung** is your clinical assistant AI. It:
- Analyzes client voice memos and session notes
- Identifies psychological frameworks (attachment patterns, defense mechanisms, etc.)
- Flags potential risk indicators
- Researches evidence-based interventions
- Generates clinical briefs before sessions

**Important:** Rung output is for your eyes only. It uses clinical language and includes detailed pattern analysis.

### 2.2 What is Beth?

**Beth** is the client-facing AI. It:
- Provides session preparation guides to clients
- Uses accessible, non-clinical language
- Suggests reflection questions
- Recommends exercises between sessions

**Important:** Beth never sees your clinical analysis. It receives only abstracted themes.

### 2.3 The Information Flow

```
Client Voice Memo
       ↓
  [Rung Analysis]  →  Clinical Brief (therapist only)
       ↓
  [Abstraction Layer]  ← Removes clinical terminology
       ↓
  [Beth Synthesis]  →  Client Guide (client sees this)
```

**Key Principle:** Your clinical insights are never shared with clients. Beth works from generalized themes only.

---

## 3. Client Onboarding

### 3.1 Adding a New Client

1. Navigate to **Clients → Add New Client**
2. Enter client information:
   - Name (encrypted)
   - Contact information (encrypted)
   - Session type (individual or couples)
3. The system generates a unique client link
4. Client receives an invitation to join

### 3.2 Obtaining Consent

Before Rung processes any client data:

1. Review the consent form with your client
2. Explain how AI assists your practice
3. Client signs digitally or on paper
4. Mark consent as "Active" in the system

**Consent Options:**
- **Full Rung**: All features enabled
- **Limited**: Voice memos only (no AI analysis)
- **Declined**: Client record only, no AI features

### 3.3 Client App Setup

Guide your client to:
1. Download the Rung client app
2. Log in with their credentials
3. Set up MFA
4. Test voice memo recording

---

## 4. Pre-Session Workflow

### 4.1 How It Works

1. **Client Records Voice Memo** (24-48 hours before session)
   - Client opens app, records thoughts
   - Recording is encrypted and uploaded

2. **Automatic Processing**
   - Voice memo is transcribed
   - Rung analyzes the content
   - Research is gathered (anonymized queries)
   - Beth generates client guide

3. **You Receive Clinical Brief**
   - Notification sent 2 hours before session
   - Review in your dashboard

### 4.2 Reading the Clinical Brief

Your clinical brief includes:

| Section | Description |
|---------|-------------|
| **Frameworks Identified** | Attachment patterns, communication styles, etc. |
| **Defense Mechanisms** | Observed defensive patterns |
| **Risk Flags** | Any concerning indicators (flagged for attention) |
| **Key Themes** | Major topics from client's memo |
| **Research Insights** | Evidence-based interventions for identified patterns |
| **Session Questions** | Suggested exploration areas |

### 4.3 Client Guide (What Your Client Sees)

Beth provides clients with:
- Friendly session preparation tips
- Reflection questions (non-clinical)
- Optional exercises
- General theme reminders

**Note:** Clients never see frameworks, defense mechanisms, or risk flags.

---

## 5. Post-Session Workflow

### 5.1 Submitting Session Notes

After each session:

1. Navigate to **Sessions → [Client Name] → Add Notes**
2. Enter your session notes
3. Notes are encrypted automatically
4. Click **Process** to trigger analysis

### 5.2 Development Plan Generation

Based on your notes, Rung:
- Extracts frameworks discussed
- Identifies progress indicators
- Generates SMART goals
- Recommends exercises
- Creates a 1-2 week sprint plan

### 5.3 Reviewing the Development Plan

Check the generated plan:
- Verify goals align with treatment direction
- Adjust exercises if needed
- Add or remove items
- Approve for client viewing

---

## 6. Couples Therapy Features

### 6.1 Creating a Couples Link

1. Both partners must be active clients
2. Navigate to **Couples → Create Link**
3. Select Partner A and Partner B
4. Confirm the link

**Important:** You must be the therapist for both partners.

### 6.2 How Couples Merge Works

When you schedule a couples session:

1. **Isolation Layer Activates**
   - Only framework-level data is extracted
   - No specific content crosses boundaries

2. **Topic Matching**
   - System identifies overlapping themes
   - Finds complementary patterns (e.g., anxious-avoidant)
   - Flags potential conflict areas

3. **Couples Brief Generated**
   - Framework names only (no details)
   - Recommended couples exercises
   - Suggested focus areas

### 6.3 What Partners See

Partners can see:
- Their own individual client guides
- Shared couples exercises
- Joint reflection prompts

Partners NEVER see:
- Each other's clinical analysis
- Individual session content
- Private risk flags

### 6.4 Pausing or Ending Couples Work

```
Couples → [Link] → Status
- Active: Full features enabled
- Paused: Merge features disabled, individual therapy continues
- Terminated: Link permanently closed
```

---

## 7. Development Plans

### 7.1 Understanding Sprint Plans

Development plans use a "sprint" model:
- **Sprint Duration**: 1-2 weeks
- **Goals**: SMART format (Specific, Measurable, Achievable, Relevant, Time-bound)
- **Exercises**: Evidence-based practices
- **Progress Tracking**: Client self-reports

### 7.2 Goal Examples

| Framework | Goal Example |
|-----------|--------------|
| Attachment | "Practice one vulnerability statement per day with partner" |
| CBT | "Complete thought record for 3 negative automatic thoughts" |
| Mindfulness | "5 minutes daily mindfulness using provided audio" |
| Gottman | "Express appreciation to partner at least once daily" |

### 7.3 Client Progress Tracking

Clients can:
- Mark exercises complete
- Rate difficulty (1-5)
- Add notes/reflections
- Request adjustments

You can view:
- Completion rates
- Difficulty patterns
- Progress over time
- Client feedback

---

## 8. Privacy and Security

### 8.1 HIPAA Compliance

Rung is fully HIPAA-compliant:
- All data encrypted at rest and in transit
- Multi-factor authentication required
- Comprehensive audit logging
- Business Associate Agreement with AWS

### 8.2 What You Should Know

| Data Type | Encryption | Access |
|-----------|------------|--------|
| Voice memos | Client-encrypted | You only |
| Session notes | Field-level encrypted | You only |
| Clinical briefs | Encrypted | You only |
| Client guides | Encrypted | Client + You |
| Audit logs | Encrypted, immutable | Compliance only |

### 8.3 Your Responsibilities

- Never share login credentials
- Log out when stepping away
- Report suspicious activity immediately
- Keep your authenticator app secure

### 8.4 Data Retention

- Clinical records: 7 years post-termination
- Voice memos: 90 days (then archived)
- Audit logs: 7 years (HIPAA requirement)

---

## 9. Best Practices

### 9.1 Getting the Most from Pre-Session Briefs

1. **Read briefs 15-30 minutes before session**
   - Fresh in your mind
   - Time to formulate questions

2. **Note any risk flags immediately**
   - Plan how to address in session
   - Document your response

3. **Use research insights**
   - Evidence-based techniques ready
   - Reference citations if helpful

### 9.2 Optimizing Voice Memos

Coach your clients to:
- Find a quiet, private space
- Speak naturally (not rehearsed)
- Focus on recent thoughts/feelings
- Keep to 5-10 minutes
- Submit 24-48 hours before session

### 9.3 Writing Effective Session Notes

For best AI analysis:
- Include frameworks/modalities discussed
- Note client breakthroughs
- Document homework assigned
- Flag progress indicators
- Mention areas for next session

### 9.4 Couples Work Guidelines

- Review merged brief before couples session
- Address complementary patterns constructively
- Use suggested exercises as starting points
- Maintain individual rapport with each partner

---

## 10. Getting Support

### 10.1 In-App Help

- Click the **?** icon for context-sensitive help
- Search the knowledge base
- View video tutorials

### 10.2 Contact Support

| Issue Type | Contact | Response Time |
|------------|---------|---------------|
| Technical issues | support@rung.health | 4 hours |
| Account problems | accounts@rung.health | 4 hours |
| Security concerns | security@rung.health | 1 hour |
| Clinical questions | clinical@rung.health | 24 hours |

### 10.3 Feedback

We want your input:
- **Feature requests**: feedback@rung.health
- **Bug reports**: bugs@rung.health
- **General feedback**: In-app feedback button

### 10.4 Community

- Monthly webinars for beta therapists
- Private Slack channel for peer discussion
- Quarterly office hours with clinical team

---

## Quick Reference Card

### Daily Workflow

```
Morning:
□ Log in and check dashboard
□ Review pre-session briefs for today's clients
□ Note any risk flags

After Each Session:
□ Enter session notes
□ Review generated development plan
□ Approve client-facing content

End of Day:
□ Check pending items
□ Review upcoming session briefs
□ Log out completely
```

### Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| New client | Ctrl+N |
| Search | Ctrl+F |
| Dashboard | Ctrl+D |
| Session notes | Ctrl+S |
| Help | F1 |

### Emergency Contacts

- **System Down**: Call (555) 123-4567
- **Security Incident**: security@rung.health + call
- **Client Crisis**: Use your existing protocols

---

## Welcome to the Beta!

Thank you for being an early adopter of Rung. Your feedback shapes the future of AI-assisted therapy.

**Your beta coordinator**: [Name] - [email]

We're excited to support your practice!

---

*Last Updated: 2026-02-02*
*Version: 1.0 Beta*

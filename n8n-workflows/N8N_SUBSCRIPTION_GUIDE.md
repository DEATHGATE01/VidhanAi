# n8n Subscription Notification System - Setup Guide

## 📋 Overview

This guide explains how to set up the subscription and email notification system using n8n workflows. The system automatically sends email notifications when bills match user subscriptions.

---

## 🎯 Workflows Included

### 1. **Subscription Notification System** (`subscription-notification-system.json`)
**Purpose:** Main workflow that checks for new bills hourly and sends instant notifications

**Trigger:** Schedule (Every hour)

**Flow:**
1. **Get New Bills** - Fetch bills introduced in last hour from API
2. **Check Bills** - Verify if any bills exist
3. **Split Bills** - Process each bill individually
4. **Get Subscriptions** - Fetch all active subscriptions
5. **Match Bills** - Match bill keywords/ministries against subscriptions
6. **Get AI Summary** - Fetch AI-generated summary for matched bills
7. **Store Notification** - Save notification to database
8. **Check Frequency** - Filter instant notifications
9. **Send Email** - Send formatted email with bill details
10. **Mark Sent** - Update notification status in database

**Key Features:**
- ✅ Case-insensitive keyword matching
- ✅ Ministry-based matching
- ✅ AI summary integration
- ✅ Duplicate prevention via database
- ✅ Professional HTML email templates

---

### 2. **Daily Digest Email** (`daily-digest-workflow.json`)
**Purpose:** Send daily digest emails at 8 AM for users with daily frequency

**Trigger:** Schedule (8:00 AM daily - cron: `0 8 * * *`)

**Flow:**
1. **Get Pending Notifications** - Fetch unsent notifications for daily frequency
2. **Check Notifications** - Verify if any exist
3. **Group by Email** - Combine multiple bills per user
4. **Generate HTML** - Create formatted bill list
5. **Send Digest** - Send consolidated email
6. **Mark All Sent** - Update all notifications in batch

**Key Features:**
- ✅ Batch processing by user
- ✅ Multiple bills in single email
- ✅ Reduces email fatigue
- ✅ Professional digest format

---

### 3. **Subscription Confirmation** (`subscription-confirmation-workflow.json`)
**Purpose:** Send welcome email when user creates new subscription

**Trigger:** Webhook (POST request)

**Flow:**
1. **Receive Webhook** - Accept POST request with subscription data
2. **Extract Data** - Parse email, keywords, ministries
3. **Format for Email** - Prepare HTML-friendly data
4. **Send Confirmation** - Send welcome email
5. **Webhook Response** - Return success/failure status

**Key Features:**
- ✅ Instant confirmation
- ✅ Displays subscription details
- ✅ Manage subscription link
- ✅ Unsubscribe option

---

## ⚙️ Prerequisites

### 1. Install n8n

**Option A: Using npm (Recommended)**
```bash
npm install -g n8n
```

**Option B: Using Docker**
```bash
docker run -it --rm \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  n8nio/n8n
```

**Option C: Desktop App**
Download from: https://n8n.io/download

### 2. Configure Email Service

n8n needs SMTP credentials to send emails. Configure in n8n:

**For Gmail:**
1. Enable 2-Factor Authentication
2. Generate App Password (Google Account → Security → App passwords)
3. In n8n: Settings → Credentials → Create New → Email (SMTP)
   - Host: `smtp.gmail.com`
   - Port: `587`
   - User: `your-email@gmail.com`
   - Password: `your-16-digit-app-password`

**For SendGrid:**
- Host: `smtp.sendgrid.net`
- Port: `587`
- User: `apikey`
- Password: `your-sendgrid-api-key`

### 3. Ensure Backend API is Running

```bash
cd backend
python app.py
```

Backend should be accessible at: `http://localhost:5000`

---

## 🚀 Installation Steps

### Step 1: Import Workflows

1. **Open n8n** - Navigate to `http://localhost:5678`

2. **Import Each Workflow:**
   - Click "Workflows" → "Add Workflow" → "Import from File"
   - Select workflow JSON file
   - Repeat for all 3 workflows

3. **Verify Imports:**
   - ✅ Subscription Notification System
   - ✅ Daily Digest Email
   - ✅ Subscription Confirmation

### Step 2: Configure Email Credentials

1. **Open Any Workflow**
2. **Click Email Send Node**
3. **Create New Credential:**
   - Name: `Gmail SMTP`
   - Host: `smtp.gmail.com`
   - Port: `587`
   - Secure: `Use TLS`
   - User: Your email
   - Password: App password
4. **Test Connection**
5. **Save Credential**

### Step 3: Update API URLs

If your Flask backend is not on `localhost:5000`, update URLs in all HTTP Request nodes:

**In Subscription Notification System:**
- Get New Bills: `http://YOUR_HOST:5000/api/bills`
- Get Subscriptions: `http://YOUR_HOST:5000/api/subscriptions`
- Get Summary: `http://YOUR_HOST:5000/api/bills/{id}/summary`
- Store Notification: `http://YOUR_HOST:5000/api/bill_notifications`

**In Daily Digest:**
- Get Pending: `http://YOUR_HOST:5000/api/bill_notifications`
- Mark Sent: `http://YOUR_HOST:5000/api/bill_notifications/{id}`

**In Subscription Confirmation:**
- Webhook path can stay as-is

### Step 4: Configure Webhook URL

For confirmation workflow:

1. **Open Subscription Confirmation Workflow**
2. **Click Webhook Node**
3. **Copy Webhook URL** (e.g., `http://localhost:5678/webhook/subscription-confirmation`)
4. **Update Frontend** to call this webhook when user subscribes

**Frontend Example:**
```javascript
// When user submits subscription form
async function subscribe(email, keywords, ministries, frequency) {
  // Create subscription in database
  const subResponse = await fetch('/api/subscriptions/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, keywords, ministries, email_frequency: frequency })
  });
  
  const subscription = await subResponse.json();
  
  // Trigger n8n confirmation workflow
  await fetch('http://localhost:5678/webhook/subscription-confirmation', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(subscription)
  });
}
```

### Step 5: Activate Workflows

1. **Subscription Notification System:**
   - Toggle "Active" switch (runs hourly automatically)

2. **Daily Digest Email:**
   - Toggle "Active" switch (runs daily at 8 AM)

3. **Subscription Confirmation:**
   - Toggle "Active" switch (webhook always listening)

---

## 🧪 Testing

### Test 1: Instant Notification

1. **Create Test Subscription:**
```bash
curl -X POST http://localhost:5000/api/subscriptions/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "keywords": ["test"],
    "ministries": ["Finance"],
    "email_frequency": "instant"
  }'
```

2. **Trigger Workflow Manually:**
   - Open "Subscription Notification System"
   - Click "Execute Workflow"
   - Check your email inbox

### Test 2: Confirmation Email

1. **Send Webhook Request:**
```bash
curl -X POST http://localhost:5678/webhook/subscription-confirmation \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "keywords": ["tax", "education"],
    "ministries": ["Finance"],
    "email_frequency": "instant",
    "subscription_id": 1
  }'
```

2. **Check Email** - Should receive confirmation

### Test 3: Daily Digest

1. **Create Multiple Notifications:**
```bash
# Create subscription with daily frequency
curl -X POST http://localhost:5000/api/subscriptions/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your-email@example.com",
    "keywords": ["tax"],
    "email_frequency": "daily"
  }'
```

2. **Manually Execute Daily Digest Workflow**
3. **Check Email** - Should receive digest

---

## 📊 Monitoring & Debugging

### View Execution History

1. **Open Workflow**
2. **Click "Executions"** tab
3. **Select Execution** to view:
   - Input/output data
   - Error messages
   - Execution time
   - Each node's result

### Common Issues

**Issue 1: "Workflow not triggering"**
- ✅ Check workflow is "Active"
- ✅ Verify schedule trigger configuration
- ✅ Check n8n is running

**Issue 2: "Email not sending"**
- ✅ Verify email credentials
- ✅ Test SMTP connection
- ✅ Check spam folder
- ✅ Verify "From" email is valid

**Issue 3: "API calls failing"**
- ✅ Ensure Flask backend is running
- ✅ Check API URL in HTTP Request nodes
- ✅ Verify API returns expected data format

**Issue 4: "Webhook not receiving data"**
- ✅ Check webhook URL is correct
- ✅ Verify webhook workflow is active
- ✅ Test with curl first

---

## 🔧 Customization

### Change Email Templates

Edit HTML in "Send Email" nodes:

1. **Open Workflow**
2. **Click Email Send Node**
3. **Edit HTML Parameter**
4. **Use n8n expressions:** `{{$json.field}}`
5. **Save & Test**

### Modify Matching Algorithm

Edit "Match Bill to Subscriptions" Code node:

```javascript
// Current: Case-insensitive partial match
if (billText.includes(keyword.toLowerCase())) {
  matched_keywords.push(keyword);
}

// Option: Exact word match
if (billText.match(new RegExp(`\\b${keyword.toLowerCase()}\\b`))) {
  matched_keywords.push(keyword);
}

// Option: Fuzzy match (add similarity check)
```

### Change Schedule

Modify Schedule Trigger nodes:

**Hourly Check:**
- Current: Every 1 hour
- Change to 30 min: `*/30 * * * *`
- Change to 2 hours: `0 */2 * * *`

**Daily Digest:**
- Current: 8 AM daily (`0 8 * * *`)
- Change to 9 AM: `0 9 * * *`
- Change to 6 PM: `0 18 * * *`

### Add Weekly Digest

Create new workflow based on `daily-digest-workflow.json`:

1. **Duplicate Workflow**
2. **Change Schedule:** `0 8 * * 1` (Monday 8 AM)
3. **Update Query:** `email_frequency=weekly`
4. **Modify Email Template** for weekly summary

---

## 📈 Performance Optimization

### For Large Datasets

**Batch Processing:**
```javascript
// Process bills in batches of 10
const bills = $json.bills || [];
const batchSize = 10;
const batches = [];

for (let i = 0; i < bills.length; i += batchSize) {
  batches.push(bills.slice(i, i + batchSize));
}

return batches.map(batch => ({json: {bills: batch}}));
```

**Rate Limiting:**
- Add "Wait" nodes between API calls
- Use n8n's built-in rate limiting

**Caching:**
- Store frequently accessed data in workflow static data
- Reduce redundant API calls

---

## 🔐 Security Best Practices

1. **Use Environment Variables:**
   - Store API keys in n8n credentials
   - Never hardcode sensitive data

2. **Webhook Authentication:**
```javascript
// Add to webhook node
const authToken = $json.headers.authorization;
if (authToken !== 'Bearer YOUR_SECRET_TOKEN') {
  throw new Error('Unauthorized');
}
```

3. **API Authentication:**
   - Add authentication headers to HTTP nodes
   - Use OAuth when available

4. **Email Validation:**
```javascript
// Validate email before sending
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
if (!emailRegex.test($json.email)) {
  throw new Error('Invalid email address');
}
```

---

## 📚 Additional Resources

- **n8n Documentation:** https://docs.n8n.io
- **n8n Community:** https://community.n8n.io
- **Email Templates:** See workflow HTML for examples
- **API Documentation:** `backend/README.md`

---

## 🐛 Troubleshooting Checklist

Before asking for help:

- [ ] n8n is running and accessible
- [ ] All workflows are active
- [ ] Email credentials configured and tested
- [ ] Flask backend is running
- [ ] API endpoints return expected data
- [ ] Checked execution history for errors
- [ ] Verified webhook URLs are correct
- [ ] Tested with manual execution first

---

## 📞 Support

For issues or questions:
1. Check execution history in n8n
2. Review logs in Flask backend
3. Test individual nodes
4. Verify data format matches expected structure
5. Check n8n community forum

---

**Last Updated:** December 9, 2025  
**Version:** 1.0.0  
**Compatible with:** n8n v1.0+, Flask 3.0+

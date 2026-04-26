# 🚀 n8n Workflow Quick Start Guide

## 📦 What You Have

I've created **3 production-ready n8n workflows** for your Regulation Alert System:

### **Workflow 1: Daily Data Collection** ⏰
- **Schedule**: Every day at 2:00 AM
- **Tasks**:
  - ✅ Scrape new bills from PRS India
  - ✅ Generate AI summaries
  - ✅ Export data for EDA
  - ✅ Send success/error notifications
- **File**: `workflow-1-daily-data-collection.json`

### **Workflow 2: Weekly Maintenance** 🔧
- **Schedule**: Every Sunday at 3:00 AM
- **Tasks**:
  - ✅ Update existing bills
  - ✅ Clear cache
  - ✅ Prefetch ministry data
  - ✅ Backup database
  - ✅ Run advanced analytics
  - ✅ Cleanup old backups
- **File**: `workflow-2-weekly-maintenance.json`

### **Workflow 3: Health Monitoring** 🏥
- **Schedule**: Every 5 minutes
- **Tasks**:
  - ✅ Check API health
  - ✅ Monitor database status
  - ✅ Scan error logs
  - ✅ Alert if issues detected
- **File**: `workflow-3-health-monitoring.json`

---

## 🎯 Installation Steps

### **Step 1: Install n8n**

Choose one method:

```bash
# Method 1: Global installation (Recommended)
npm install n8n -g

# Method 2: Run with npx (No installation)
npx n8n

# Method 3: Docker
docker run -it --rm --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n
```

### **Step 2: Start n8n**

```bash
# If installed globally
n8n

# If using npx
npx n8n

# Access UI at: http://localhost:5678
```

### **Step 3: Set Up Email Credentials**

1. Open n8n UI at `http://localhost:5678`
2. Go to **Settings** → **Credentials**
3. Click **Add Credential** → Select **SMTP**
4. Configure:
   - **Name**: Gmail SMTP
   - **Host**: smtp.gmail.com
   - **Port**: 587
   - **User**: your-email@gmail.com
   - **Password**: Your Google App Password (not regular password)
   
   **To create App Password:**
   1. Go to https://myaccount.google.com/security
   2. Enable 2-Step Verification
   3. Go to App Passwords
   4. Generate password for "Mail"
   5. Copy and paste in n8n

### **Step 4: Import Workflows**

For each workflow file:

1. In n8n UI, click **Workflows** (left sidebar)
2. Click **Import from File** button
3. Select the JSON file:
   - `workflow-1-daily-data-collection.json`
   - `workflow-2-weekly-maintenance.json`
   - `workflow-3-health-monitoring.json`
4. Click **Import**

### **Step 5: Configure Paths**

⚠️ **IMPORTANT**: Update these paths in ALL workflows:

Replace:
```
D:\\internship\\BDA\\regulation-alert-system\\backend
```

With your actual path (use double backslashes):
```
YOUR_ACTUAL_PATH_HERE
```

**Where to change:**
- In each "Execute Command" node
- Click on the node
- Update the `command` parameter
- Click **Save**

### **Step 6: Update Email Addresses**

In each workflow, update:
- **From Email**: your-email@gmail.com
- **To Email**: admin@example.com (or your email)

### **Step 7: Activate Workflows**

1. Open each workflow
2. Click the **Activate** toggle (top right)
3. Workflow will now run automatically on schedule

---

## ✅ Verify Installation

### **Test Health Monitoring** (Runs every 5 min)
```bash
# Make sure your Flask server is running
cd D:\internship\BDA\regulation-alert-system\backend
.venv\Scripts\Activate.ps1
python app.py

# Check if health endpoint works
curl http://localhost:5000/api/health
```

### **Test Manual Execution**
1. Open any workflow in n8n
2. Click **Execute Workflow** button (top right)
3. Watch the execution in real-time
4. Check for errors

---

## 📊 What Each Workflow Does

### **Workflow 1: Daily Data Collection**
```
02:00 AM
   ↓
Log Start → Fetch Bills (100 batch, 0.3s delay)
   ↓
Check Success?
   ├─ YES → Generate Summaries → Export Data → ✅ Success Email
   └─ NO → ❌ Error Email
```

### **Workflow 2: Weekly Maintenance**
```
Sunday 03:00 AM
   ↓
Update Bills → Clear Cache → Prefetch Ministries
   ↓
Backup DB → Cleanup Old Backups → Run Analytics
   ↓
📧 Weekly Report Email
```

### **Workflow 3: Health Monitoring**
```
Every 5 Minutes
   ↓
Check API (/api/health)
   ├─ Healthy → Check DB → Check Logs → 📝 Log Status
   └─ Unhealthy → 🚨 CRITICAL ALERT EMAIL
```

---

## 🔧 Customization Options

### **Change Schedule Times**

In the workflow, click on the Schedule Trigger node:

**For Daily Workflow:**
```json
{
  "rule": {
    "hour": 2,  // Change to your preferred hour (0-23)
    "minute": 0,
    "timezone": "Asia/Kolkata"  // Change timezone
  }
}
```

**For Weekly Workflow:**
```json
{
  "rule": {
    "cronExpression": "0 3 * * 0"  // 0=Sunday, change to 1-6 for other days
  }
}
```

### **Adjust Batch Sizes**

In "Fetch New Bills" node command:
```bash
# Current: --batch-size 100 --delay 0.3
# For faster (but riskier): --batch-size 200 --delay 0.2
# For safer (but slower): --batch-size 50 --delay 0.5
```

### **Add Slack Notifications**

1. Create Slack Webhook: https://api.slack.com/messaging/webhooks
2. Add new node: **Slack → Send Message**
3. Configure webhook URL
4. Connect after success/error nodes

---

## 📧 Email Notification Samples

### **✅ Success Email**
```
Subject: ✅ Daily Bill Scraping Complete - 2025-12-09

Daily Regulation Alert System Report

📊 Summary:
• Bills processed: 938
• Summaries generated: 30
• Data exported: 938 records
• Execution time: 1823476 ms
• Status: ✅ Success

Timestamp: 2025-12-09 02:45:32

This is an automated message from the Regulation Alert System.
```

### **❌ Error Email**
```
Subject: ❌ Daily Bill Scraping Failed - 2025-12-09

⚠️ Regulation Alert System - Error Report

❌ The daily bill scraping process has failed.

Error Details:
ConnectionError: Failed to connect to PRS India website

Exit Code: 1

Timestamp: 2025-12-09 02:15:18

Please check the logs and take corrective action.
```

### **🚨 Critical Alert**
```
Subject: 🚨 CRITICAL: Regulation Alert System is DOWN

⚠️ CRITICAL ALERT

The Regulation Alert System API is not responding or unhealthy.

Timestamp: 2025-12-09 14:35:22

🔍 Please investigate immediately:
1. Check if Flask server is running
2. Review application logs
3. Check database connectivity
4. Verify system resources
```

---

## 🐛 Troubleshooting

### **Workflow Not Running**
- ✅ Check if workflow is **Activated** (toggle on)
- ✅ Verify n8n is running (`n8n` command)
- ✅ Check system time matches schedule time
- ✅ Review execution history for errors

### **Email Not Sending**
- ✅ Verify Gmail App Password (not regular password)
- ✅ Check credentials in Settings → Credentials
- ✅ Test SMTP connection: Port 587, TLS enabled
- ✅ Check spam/junk folder

### **Command Not Executing**
- ✅ Verify Python virtual environment path
- ✅ Check paths use double backslashes (`\\`)
- ✅ Test command manually in PowerShell first
- ✅ Ensure Python scripts exist and are executable

### **Permission Errors**
```bash
# Run PowerShell as Administrator
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📈 Monitoring Dashboard

Create a simple monitoring page:

```html
<!-- save as: monitoring.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Regulation Alert - Status</title>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <h1>🚀 Regulation Alert System Status</h1>
    <div id="status"></div>
    
    <script>
        fetch('http://localhost:5000/api/health')
            .then(r => r.json())
            .then(data => {
                document.getElementById('status').innerHTML = 
                    `<h2>✅ Status: ${data.status}</h2>
                     <p>Timestamp: ${data.timestamp}</p>`;
            })
            .catch(e => {
                document.getElementById('status').innerHTML = 
                    `<h2>❌ System Down</h2><p>${e}</p>`;
            });
    </script>
</body>
</html>
```

---

## 🎉 Summary

You now have:
- ✅ **3 automated workflows** running 24/7
- ✅ **Daily scraping** at 2 AM
- ✅ **Weekly maintenance** on Sundays
- ✅ **Health monitoring** every 5 minutes
- ✅ **Email alerts** for success/errors
- ✅ **Automatic backups** and cleanup
- ✅ **EDA data exports** for analysis

**Total automation**: ~95% of manual tasks eliminated! 🚀

---

## 📚 Next Steps

1. ✅ **Monitor**: Check emails for first few days
2. ✅ **Adjust**: Fine-tune schedules and batch sizes
3. ✅ **Expand**: Add Slack/SMS notifications
4. ✅ **Scale**: Add more workflows as needed
5. ✅ **Document**: Track any issues and improvements

---

## 🆘 Support

- **n8n Docs**: https://docs.n8n.io/
- **Community**: https://community.n8n.io/
- **Workflows**: https://n8n.io/workflows/

**Happy Automating! 🎊**

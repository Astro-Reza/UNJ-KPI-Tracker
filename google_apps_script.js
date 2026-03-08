/**
 * KPI Dashboard — Google Apps Script Backend
 * 
 * This script acts as a JSON REST API for 3 sheets in this spreadsheet:
 *   Sheet1 (student_data)  — headers: name_id, email_id, department_id, nim_id, score, job_id_list, password
 *   Sheet2 (task_data)     — headers: task_id, task_name, type_id, start_date, end_date, status_id, pic, related_links, description
 *   Sheet3 (task_contributors) — headers: task_id, nim_id, points
 *
 * DEPLOYMENT:
 *   1. Open your Google Sheet → Extensions → Apps Script
 *   2. Replace the default Code.gs content with this entire file
 *   3. Click Deploy → New deployment → Web app
 *      - Execute as: Me
 *      - Who has access: Anyone
 *   4. Copy the URL and paste it as WEB_APP_URL in app.py
 */

const SHEET_NAMES = {
  students: 'student_data',
  tasks: 'task_data',
  contributors: 'task_contributors'
};

const HEADERS = {
  students: ['name_id', 'email_id', 'department_id', 'nim_id', 'score', 'job_id_list', 'password'],
  tasks: ['task_id', 'task_name', 'type_id', 'start_date', 'end_date', 'status_id', 'pic', 'related_links', 'description'],
  contributors: ['task_id', 'nim_id', 'points']
};

// ── Helpers ─────────────────────────────────────────

function getOrCreateSheet(name, headers) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    sheet.appendRow(headers);
  }
  return sheet;
}

function sheetToJson(sheet) {
  const data = sheet.getDataRange().getValues();
  if (data.length <= 1) return []; // only header row
  const headers = data[0];
  const rows = [];
  for (let i = 1; i < data.length; i++) {
    const obj = {};
    for (let j = 0; j < headers.length; j++) {
      obj[headers[j]] = data[i][j] !== undefined ? String(data[i][j]) : '';
    }
    rows.push(obj);
  }
  return rows;
}

function jsonToSheet(sheet, headers, rows) {
  // Clear everything below header
  sheet.clear();
  sheet.appendRow(headers);
  
  if (rows.length > 0) {
    const values = rows.map(row => headers.map(h => row[h] !== undefined ? row[h] : ''));
    sheet.getRange(2, 1, values.length, headers.length).setValues(values);
  }
}

function jsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

// ── API Handler ─────────────────────────────────────

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const action = body.action;

    switch (action) {
      // ── Students ────────────────────────────────
      case 'getStudents': {
        const sheet = getOrCreateSheet(SHEET_NAMES.students, HEADERS.students);
        return jsonResponse({ success: true, data: sheetToJson(sheet) });
      }
      case 'saveStudents': {
        const sheet = getOrCreateSheet(SHEET_NAMES.students, HEADERS.students);
        jsonToSheet(sheet, HEADERS.students, body.data || []);
        return jsonResponse({ success: true, message: 'Students saved' });
      }

      // ── Tasks ───────────────────────────────────
      case 'getTasks': {
        const sheet = getOrCreateSheet(SHEET_NAMES.tasks, HEADERS.tasks);
        return jsonResponse({ success: true, data: sheetToJson(sheet) });
      }
      case 'saveTasks': {
        const sheet = getOrCreateSheet(SHEET_NAMES.tasks, HEADERS.tasks);
        jsonToSheet(sheet, HEADERS.tasks, body.data || []);
        return jsonResponse({ success: true, message: 'Tasks saved' });
      }

      // ── Contributors ────────────────────────────
      case 'getContributors': {
        const sheet = getOrCreateSheet(SHEET_NAMES.contributors, HEADERS.contributors);
        return jsonResponse({ success: true, data: sheetToJson(sheet) });
      }
      case 'saveContributors': {
        const sheet = getOrCreateSheet(SHEET_NAMES.contributors, HEADERS.contributors);
        jsonToSheet(sheet, HEADERS.contributors, body.data || []);
        return jsonResponse({ success: true, message: 'Contributors saved' });
      }

      default:
        return jsonResponse({ success: false, error: 'Unknown action: ' + action });
    }
  } catch (err) {
    return jsonResponse({ success: false, error: err.message });
  }
}

function doGet(e) {
  return jsonResponse({ success: true, message: 'KPI Dashboard API is running. Use POST requests.' });
}

<?php
// SQE1 Progress API — bidouillecode.dev/solicitor/progress.php
$DB_HOST = 'localhost';
$DB_NAME = 'u256011742_solicitor';
$DB_USER = 'u256011742_solicitor';
$DB_PASS = '#Patience13#';

// CORS — allow GitHub Pages and any origin
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { http_response_code(200); exit; }

try {
    $pdo = new PDO("mysql:host=$DB_HOST;dbname=$DB_NAME;charset=utf8mb4", $DB_USER, $DB_PASS);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(['error' => 'DB connection failed']);
    exit;
}

// Create table if needed
$pdo->exec("CREATE TABLE IF NOT EXISTS sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    datetime VARCHAR(64) NOT NULL UNIQUE,
    paper VARCHAR(32),
    percentage FLOAT,
    correct INT,
    totalQ INT,
    durationMode INT,
    subjects JSON,
    questions JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)");

$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'GET') {
    $stmt = $pdo->query("SELECT datetime, paper, percentage, correct, totalQ, durationMode, subjects, questions FROM sessions ORDER BY datetime ASC");
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    foreach ($rows as &$r) {
        $r['percentage'] = (float)$r['percentage'];
        $r['correct']    = (int)$r['correct'];
        $r['totalQ']     = (int)$r['totalQ'];
        $r['durationMode'] = (int)$r['durationMode'];
        $r['subjects']   = json_decode($r['subjects'] ?? '{}', true);
        $r['questions']  = json_decode($r['questions'] ?? '[]', true);
    }
    echo json_encode(array_values($rows));

} elseif ($method === 'POST') {
    $body = json_decode(file_get_contents('php://input'), true);
    if (!$body) { http_response_code(400); echo json_encode(['error'=>'Invalid JSON']); exit; }

    // Delete
    if (isset($body['delete_datetime'])) {
        $stmt = $pdo->prepare("DELETE FROM sessions WHERE datetime = ?");
        $stmt->execute([$body['delete_datetime']]);
        echo json_encode(['ok' => true]);
        exit;
    }

    // Save session
    $stmt = $pdo->prepare("INSERT IGNORE INTO sessions
        (datetime, paper, percentage, correct, totalQ, durationMode, subjects, questions)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)");
    $stmt->execute([
        $body['datetime']    ?? date('c'),
        $body['paper']       ?? '',
        $body['percentage']  ?? 0,
        $body['correct']     ?? 0,
        $body['totalQ']      ?? 0,
        $body['durationMode'] ?? 0,
        json_encode($body['subjects']  ?? []),
        json_encode($body['questions'] ?? [])
    ]);
    echo json_encode(['ok' => true]);

} else {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
}
?>

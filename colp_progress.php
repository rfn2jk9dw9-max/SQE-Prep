<?php
// SQE1 COLP Revision Progress API — bidouillecode.dev/solicitor/colp_progress.php
// Stores the set of completed chapter codes for the COLP revision schedule.
$DB_HOST = 'localhost';
$DB_NAME = 'u256011742_solicitor';
$DB_USER = 'u256011742_solicitor';
$DB_PASS = '#Patience13#';

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

// Create table if needed (one row per user key — future-proof)
$pdo->exec("CREATE TABLE IF NOT EXISTS colp_progress (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_key VARCHAR(64) NOT NULL UNIQUE,
    done_codes JSON NOT NULL DEFAULT ('[]'),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)");

$USER_KEY = 'ghita';

$method = $_SERVER['REQUEST_METHOD'];

if ($method === 'GET') {
    $stmt = $pdo->prepare("SELECT done_codes FROM colp_progress WHERE user_key = ?");
    $stmt->execute([$USER_KEY]);
    $row = $stmt->fetch(PDO::FETCH_ASSOC);
    $codes = $row ? json_decode($row['done_codes'], true) : [];
    echo json_encode(['done' => $codes]);

} elseif ($method === 'POST') {
    $body = json_decode(file_get_contents('php://input'), true);
    if (!isset($body['done']) || !is_array($body['done'])) {
        http_response_code(400);
        echo json_encode(['error' => 'Expected {"done": [...codes]}']);
        exit;
    }
    $codes_json = json_encode(array_values($body['done']));
    $stmt = $pdo->prepare("INSERT INTO colp_progress (user_key, done_codes)
        VALUES (?, ?)
        ON DUPLICATE KEY UPDATE done_codes = VALUES(done_codes)");
    $stmt->execute([$USER_KEY, $codes_json]);
    echo json_encode(['ok' => true, 'count' => count($body['done'])]);

} else {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
}
?>

// Canvas and context setup
const canvas = document.getElementById('pongCanvas');
const ctx = canvas.getContext('2d');

// Game objects
const paddleWidth = 10;
const paddleHeight = 80;
const ballSize = 8;

// Player paddle (left)
const player = {
    x: 10,
    y: canvas.height / 2 - paddleHeight / 2,
    width: paddleWidth,
    height: paddleHeight,
    dy: 0,
    speed: 6
};

// Computer paddle (right)
const computer = {
    x: canvas.width - paddleWidth - 10,
    y: canvas.height / 2 - paddleHeight / 2,
    width: paddleWidth,
    height: paddleHeight,
    dy: 0,
    speed: 5
};

// Ball
const ball = {
    x: canvas.width / 2,
    y: canvas.height / 2,
    dx: 5,
    dy: 5,
    size: ballSize,
    speed: 5
};

// Scores
let playerScore = 0;
let computerScore = 0;

// Input handling
const keys = {};

document.addEventListener('keydown', (e) => {
    keys[e.key] = true;
});

document.addEventListener('keyup', (e) => {
    keys[e.key] = false;
});

// Mouse tracking for player paddle
document.addEventListener('mousemove', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mouseY = e.clientY - rect.top;
    
    // Smooth mouse following
    const targetY = mouseY - player.height / 2;
    if (Math.abs(targetY - player.y) > 5) {
        player.y += (targetY - player.y) * 0.1;
    }
});

// Update function
function update() {
    // Player movement with arrow keys
    if (keys['ArrowUp'] || keys['w'] || keys['W']) {
        player.y -= player.speed;
    }
    if (keys['ArrowDown'] || keys['s'] || keys['S']) {
        player.y += player.speed;
    }

    // Keep player paddle in bounds
    if (player.y < 0) player.y = 0;
    if (player.y + player.height > canvas.height) {
        player.y = canvas.height - player.height;
    }

    // Computer AI - follow the ball with some lag
    const computerCenter = computer.y + computer.height / 2;
    const ballCenter = ball.y;
    
    if (computerCenter < ballCenter - 35) {
        computer.y += computer.speed;
    } else if (computerCenter > ballCenter + 35) {
        computer.y -= computer.speed;
    }

    // Keep computer paddle in bounds
    if (computer.y < 0) computer.y = 0;
    if (computer.y + computer.height > canvas.height) {
        computer.y = canvas.height - computer.height;
    }

    // Ball movement
    ball.x += ball.dx;
    ball.y += ball.dy;

    // Ball collision with top and bottom walls
    if (ball.y - ball.size < 0 || ball.y + ball.size > canvas.height) {
        ball.dy = -ball.dy;
        ball.y = Math.max(ball.size, Math.min(canvas.height - ball.size, ball.y));
    }

    // Ball collision with paddles
    // Player paddle collision
    if (
        ball.x - ball.size < player.x + player.width &&
        ball.y > player.y &&
        ball.y < player.y + player.height
    ) {
        ball.dx = -ball.dx;
        ball.x = player.x + player.width + ball.size;
        
        // Add spin based on where ball hits paddle
        const collidePoint = ball.y - (player.y + player.height / 2);
        ball.dy = (collidePoint / (player.height / 2)) * ball.speed;
    }

    // Computer paddle collision
    if (
        ball.x + ball.size > computer.x &&
        ball.y > computer.y &&
        ball.y < computer.y + computer.height
    ) {
        ball.dx = -ball.dx;
        ball.x = computer.x - ball.size;
        
        // Add spin based on where ball hits paddle
        const collidePoint = ball.y - (computer.y + computer.height / 2);
        ball.dy = (collidePoint / (computer.height / 2)) * ball.speed;
    }

    // Ball out of bounds - scoring
    if (ball.x - ball.size < 0) {
        computerScore++;
        document.getElementById('computerScore').textContent = computerScore;
        resetBall();
    }

    if (ball.x + ball.size > canvas.width) {
        playerScore++;
        document.getElementById('playerScore').textContent = playerScore;
        resetBall();
    }
}

// Reset ball to center
function resetBall() {
    ball.x = canvas.width / 2;
    ball.y = canvas.height / 2;
    ball.dx = (Math.random() > 0.5 ? 1 : -1) * 5;
    ball.dy = (Math.random() - 0.5) * 8;
}

// Draw function
function draw() {
    // Clear canvas with gradient
    const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
    gradient.addColorStop(0, '#1a1a2e');
    gradient.addColorStop(0.5, '#16213e');
    gradient.addColorStop(1, '#1a1a2e');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw center line (dashed)
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
    ctx.setLineDash([10, 10]);
    ctx.beginPath();
    ctx.moveTo(canvas.width / 2, 0);
    ctx.lineTo(canvas.width / 2, canvas.height);
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw player paddle
    ctx.fillStyle = '#00d4ff';
    ctx.shadowColor = '#00d4ff';
    ctx.shadowBlur = 10;
    ctx.fillRect(player.x, player.y, player.width, player.height);
    ctx.shadowBlur = 0;

    // Draw computer paddle
    ctx.fillStyle = '#ff006e';
    ctx.shadowColor = '#ff006e';
    ctx.shadowBlur = 10;
    ctx.fillRect(computer.x, computer.y, computer.width, computer.height);
    ctx.shadowBlur = 0;

    // Draw ball
    ctx.fillStyle = '#ffd700';
    ctx.shadowColor = '#ffd700';
    ctx.shadowBlur = 15;
    ctx.beginPath();
    ctx.arc(ball.x, ball.y, ball.size, 0, Math.PI * 2);
    ctx.fill();
    ctx.shadowBlur = 0;
}

// Game loop
function gameLoop() {
    update();
    draw();
    requestAnimationFrame(gameLoop);
}

// Start the game
gameLoop();
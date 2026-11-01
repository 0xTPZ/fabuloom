/** Reusable, provider-independent 2D character rig and Canvas renderer. */

export class CharacterNode {
  constructor(id, children = []) {
    this.id = id;
    this.children = children;
  }
}

export class CharacterRig {
  constructor() {
    this.root = new CharacterNode("character", [
      new CharacterNode("body"),
      new CharacterNode("head", [
        new CharacterNode("eyes", [new CharacterNode("left-eye"), new CharacterNode("right-eye")]),
        new CharacterNode("mouth"),
      ]),
    ]);
    this.speechAmplitude = 0;
    this.currentPose = { breathing: 0, head_rotation: 0, eye_open: 1, mouth_open: 0 };
    this.nextBlinkAt = 4200;
    this.blinkStartedAt = -1;
  }

  setSpeechAmplitude(amplitude) {
    this.speechAmplitude = Math.max(0, Math.min(1, Number(amplitude) || 0));
  }

  update(timeMs, isPlaying) {
    const seconds = timeMs / 1000;
    const breathing = (Math.sin(seconds * Math.PI * 1.8) + 1) / 2;
    const headRotation = Math.sin(seconds * 0.7) * 0.035 + Math.sin(seconds * 0.31) * 0.018;
    if (timeMs >= this.nextBlinkAt && this.blinkStartedAt < 0) {
      this.blinkStartedAt = timeMs;
      this.nextBlinkAt = timeMs + 3800 + ((Math.sin(seconds * 1.7) + 1) * 700);
    }
    let eyeOpen = 1;
    if (this.blinkStartedAt >= 0) {
      const elapsed = timeMs - this.blinkStartedAt;
      if (elapsed <= 130) {
        eyeOpen = 1 - elapsed / 130;
      } else if (elapsed <= 260) {
        eyeOpen = (elapsed - 130) / 130;
      } else {
        this.blinkStartedAt = -1;
      }
    }
    const mouthOpen = isPlaying ? this.speechAmplitude : 0;
    this.currentPose = { breathing, head_rotation: headRotation, eye_open: eyeOpen, mouth_open: mouthOpen };
  }

  pose() {
    return { ...this.currentPose };
  }
}

export class CanvasCharacterRenderer {
  constructor(canvas, rig) {
    this.canvas = canvas;
    this.context = canvas.getContext("2d");
    this.rig = rig;
  }

  render() {
    const ctx = this.context;
    const width = this.canvas.width;
    const height = this.canvas.height;
    const pose = this.rig.pose();
    ctx.clearRect(0, 0, width, height);
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, "#13233f");
    gradient.addColorStop(1, "#08101f");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, width, height);

    ctx.fillStyle = "rgba(109, 160, 255, 0.10)";
    ctx.beginPath();
    ctx.ellipse(width * 0.5, height * 0.87, width * 0.29, height * 0.08, 0, 0, Math.PI * 2);
    ctx.fill();

    const centerX = width * 0.5;
    const bodyY = height * 0.76 + pose.breathing * 2;
    ctx.save();
    ctx.translate(centerX, bodyY);
    ctx.fillStyle = "#4361b2";
    ctx.beginPath();
    ctx.ellipse(0, 0, width * 0.19, height * 0.21, 0, Math.PI, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#f4c7a1";
    ctx.beginPath();
    ctx.arc(0, -height * 0.27, width * 0.125, 0, Math.PI * 2);
    ctx.fill();

    ctx.save();
    ctx.rotate(pose.head_rotation);
    ctx.fillStyle = "#2b1e3f";
    ctx.beginPath();
    ctx.arc(0, -height * 0.30, width * 0.13, Math.PI, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#f4c7a1";
    ctx.beginPath();
    ctx.arc(-width * 0.126, -height * 0.27, width * 0.018, 0, Math.PI * 2);
    ctx.arc(width * 0.126, -height * 0.27, width * 0.018, 0, Math.PI * 2);
    ctx.fill();

    this.drawEye(ctx, -width * 0.045, -height * 0.31, pose.eye_open);
    this.drawEye(ctx, width * 0.045, -height * 0.31, pose.eye_open);
    ctx.strokeStyle = "#7c4937";
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(-width * 0.012, -height * 0.245);
    ctx.quadraticCurveTo(0, -height * 0.232, width * 0.012, -height * 0.245);
    ctx.stroke();

    const mouthHeight = 4 + pose.mouth_open * height * 0.045;
    ctx.fillStyle = pose.mouth_open > 0.08 ? "#5b2542" : "#9a4c5a";
    ctx.beginPath();
    ctx.ellipse(0, -height * 0.215, width * 0.034, mouthHeight, 0, 0, Math.PI * 2);
    ctx.fill();
    if (pose.mouth_open > 0.12) {
      ctx.fillStyle = "#f6d7c1";
      ctx.beginPath();
      ctx.ellipse(0, -height * 0.217, width * 0.019, Math.max(2, mouthHeight * 0.24), 0, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
    ctx.restore();
  }

  drawEye(ctx, x, y, openness) {
    ctx.save();
    ctx.translate(x, y);
    ctx.scale(1, Math.max(0.04, openness));
    ctx.fillStyle = "#fffaf2";
    ctx.beginPath();
    ctx.ellipse(0, 0, 15, 11, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#253a68";
    ctx.beginPath();
    ctx.arc(0, 0, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
}

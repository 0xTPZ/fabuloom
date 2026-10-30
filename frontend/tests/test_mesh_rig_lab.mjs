import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const contractPath = new URL('../../labs/mesh-rig/contract.json', import.meta.url);
const evidencePath = 'E:/Fabuloom/workspace/exports/mesh-rig-lab/poses/mesh-rig-evidence.json';

test('Mission 016 contract defines a weighted mesh hierarchy', () => {
  const contract = JSON.parse(fs.readFileSync(contractPath, 'utf8'));
  assert.deepEqual(contract.bone_hierarchy, ['Shoulder', 'UpperArm', 'Elbow', 'Forearm', 'WristHand']);
  assert.deepEqual(contract.grid, { columns: 8, rows: 12, vertices_per_tile: 4 });
  assert.deepEqual(contract.required_poses, ['rest', 'elbow_45', 'elbow_90', 'hand_raised', 'pointing']);
  assert.equal(contract.official_assets_modified, false);
});

test('Mission 016 generated evidence confirms non-rigid deformation', { skip: !fs.existsSync(evidencePath) }, () => {
  const evidence = JSON.parse(fs.readFileSync(evidencePath, 'utf8'));
  assert.deepEqual(evidence.rig.bone_hierarchy, ['Shoulder', 'UpperArm', 'Elbow', 'Forearm', 'WristHand']);
  assert.equal(evidence.rig.bone_count, 5);
  assert.equal(evidence.rig.polygon_tile_count, 96);
  assert.equal(evidence.rig.grid.vertices_per_tile, 4);
  for (const sum of evidence.rig.weight_normalization_samples) assert.ok(Math.abs(sum - 1) < 1e-6);
  const byPose = new Map(evidence.poses.map((pose) => [pose.pose, pose.max_displacement]));
  assert.equal(byPose.get('rest'), 0);
  for (const pose of ['elbow_45', 'elbow_90', 'hand_raised', 'pointing']) assert.ok(byPose.get(pose) > 1);
});

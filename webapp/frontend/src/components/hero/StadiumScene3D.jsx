import { Canvas, useFrame } from '@react-three/fiber';
import { useMemo, useRef } from 'react';
import * as THREE from 'three';

function FloodlightTower({ position, aimTarget = [0, 0, 0], beamColor = '#D8B45A' }) {
  const [x, y, z] = position;
  const beamProps = useMemo(() => {
    const start = new THREE.Vector3(x, y + 6.4, z);
    const end = new THREE.Vector3(...aimTarget);
    const dir = new THREE.Vector3().subVectors(end, start);
    const length = dir.length();
    const mid = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
    const quat = new THREE.Quaternion().setFromUnitVectors(
      new THREE.Vector3(0, -1, 0),
      dir.clone().normalize()
    );
    return { mid, quat, length };
  }, [x, y, z, aimTarget]);

  return (
    <group>
      {/* Tower mast */}
      <mesh position={[x, y + 3.1, z]}>
        <cylinderGeometry args={[0.12, 0.24, 6.4, 8]} />
        <meshStandardMaterial color="#392940" metalness={0.6} roughness={0.4} />
      </mesh>
      {/* Floodlight bank */}
      <mesh position={[x, y + 6.4, z]}>
        <boxGeometry args={[1.6, 0.75, 0.35]} />
        <meshBasicMaterial color="#FFF4DC" />
      </mesh>
      {/* Volumetric translucent light cone */}
      <mesh position={beamProps.mid} quaternion={beamProps.quat}>
        <coneGeometry args={[4.4, beamProps.length, 24, 1, true]} />
        <meshBasicMaterial
          color={beamColor}
          transparent
          opacity={0.075}
          side={THREE.DoubleSide}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
}

function CricketPitchAndBowl() {
  return (
    <group position={[0, -2.4, 0]}>
      {/* Night outfield */}
      <mesh rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[16.5, 64]} />
        <meshStandardMaterial color="#192524" roughness={0.92} metalness={0.05} />
      </mesh>

      {/* 30-yard inner circle line */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.015, 0]}>
        <ringGeometry args={[6.95, 7.05, 64]} />
        <meshBasicMaterial color="#B8A6C2" transparent opacity={0.28} />
      </mesh>

      {/* Boundary rope */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <ringGeometry args={[14.2, 14.35, 64]} />
        <meshBasicMaterial color="#E83E80" transparent opacity={0.55} />
      </mesh>

      {/* Central 22-yard cricket pitch strip */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.025, 0]}>
        <planeGeometry args={[1.65, 8.8]} />
        <meshStandardMaterial color="#8E795E" roughness={0.85} />
      </mesh>

      {/* Popping creases */}
      {[-3.6, 3.6].map((zPos) => (
        <mesh key={zPos} rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.032, zPos]}>
          <planeGeometry args={[1.65, 0.07]} />
          <meshBasicMaterial color="#F5F1F5" transparent opacity={0.85} />
        </mesh>
      ))}

      {/* Miniature wickets at both ends */}
      {[-4.05, 4.05].map((zPos) => (
        <group key={`wk-${zPos}`} position={[0, 0.25, zPos]}>
          {[-0.14, 0, 0.14].map((xPos) => (
            <mesh key={xPos} position={[xPos, 0, 0]}>
              <cylinderGeometry args={[0.02, 0.02, 0.5, 6]} />
              <meshStandardMaterial color="#D8B45A" emissive="#D8B45A" emissiveIntensity={0.35} />
            </mesh>
          ))}
        </group>
      ))}

      {/* Lower stadium grandstand bowl */}
      <mesh position={[0, 1.5, 0]}>
        <cylinderGeometry args={[19.5, 16.4, 3.2, 48, 1, true]} />
        <meshStandardMaterial color="#24172C" roughness={0.85} side={THREE.BackSide} />
      </mesh>

      {/* Upper stadium tier */}
      <mesh position={[0, 4.3, 0]}>
        <cylinderGeometry args={[22.2, 19.6, 2.8, 48, 1, true]} />
        <meshStandardMaterial color="#392940" roughness={0.8} side={THREE.BackSide} />
      </mesh>

      {/* Illuminated Royals Pink & Gold stadium fascia rings */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 3.05, 0]}>
        <ringGeometry args={[19.2, 19.45, 64]} />
        <meshBasicMaterial color="#E83E80" transparent opacity={0.75} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 5.65, 0]}>
        <ringGeometry args={[21.9, 22.15, 64]} />
        <meshBasicMaterial color="#D8B45A" transparent opacity={0.5} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function HeroCricketBall() {
  const ballRef = useRef(null);

  useFrame((state, delta) => {
    if (!ballRef.current) return;
    ballRef.current.rotation.y += delta * 0.45;
    ballRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.6) * 0.18 + 0.3;
    ballRef.current.position.y = 0.55 + Math.sin(state.clock.elapsedTime * 1.1) * 0.18;
  });

  return (
    <group ref={ballRef} position={[2.35, 0.55, 3.2]}>
      {/* Crimson-pink leather sphere */}
      <mesh>
        <sphereGeometry args={[0.92, 48, 48]} />
        <meshStandardMaterial
          color="#9E1B4F"
          emissive="#450A22"
          emissiveIntensity={0.35}
          roughness={0.28}
          metalness={0.25}
        />
      </mesh>
      {/* Primary metallic gold stitched seam */}
      <mesh rotation={[Math.PI / 2, 0, 0.2]}>
        <torusGeometry args={[0.928, 0.032, 12, 64]} />
        <meshStandardMaterial color="#D8B45A" emissive="#D8B45A" emissiveIntensity={0.55} metalness={0.75} roughness={0.25} />
      </mesh>
      {/* Parallel twin seam stitch rings */}
      <mesh rotation={[Math.PI / 2, 0, 0.2]} position={[0, 0.055, 0]}>
        <torusGeometry args={[0.918, 0.012, 8, 64]} />
        <meshBasicMaterial color="#F5F1F5" transparent opacity={0.75} />
      </mesh>
      <mesh rotation={[Math.PI / 2, 0, 0.2]} position={[0, -0.055, 0]}>
        <torusGeometry args={[0.918, 0.012, 8, 64]} />
        <meshBasicMaterial color="#F5F1F5" transparent opacity={0.75} />
      </mesh>
    </group>
  );
}

function AtmosphericParticles() {
  const pointsRef = useRef(null);

  const positions = useMemo(() => {
    const count = 300;
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i += 1) {
      const r = 3 + Math.random() * 16;
      const theta = Math.random() * Math.PI * 2;
      arr[i * 3] = Math.cos(theta) * r;
      arr[i * 3 + 1] = -1.5 + Math.random() * 9.5;
      arr[i * 3 + 2] = Math.sin(theta) * r;
    }
    return arr;
  }, []);

  useFrame((state) => {
    if (!pointsRef.current) return;
    pointsRef.current.rotation.y = state.clock.elapsedTime * 0.025;
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} />
      </bufferGeometry>
      <pointsMaterial color="#F5D996" size={0.09} transparent opacity={0.65} sizeAttenuation depthWrite={false} />
    </points>
  );
}

function CinematicCameraRig() {
  useFrame((state) => {
    const t = state.clock.elapsedTime;
    const targetX = Math.sin(t * 0.16) * 2.2 + state.pointer.x * 0.9;
    const targetY = 3.0 + Math.sin(t * 0.24) * 0.35 + state.pointer.y * 0.45;
    state.camera.position.x = THREE.MathUtils.lerp(state.camera.position.x, targetX, 0.035);
    state.camera.position.y = THREE.MathUtils.lerp(state.camera.position.y, targetY, 0.035);
    state.camera.position.z = 11.4;
    state.camera.lookAt(0, -0.4, 0);
  });
  return null;
}

export default function StadiumScene3D({ active = true }) {
  if (!active) return null;

  return (
    <div className="absolute inset-0 h-full w-full" aria-hidden="true">
      <Canvas
        dpr={[1, 1.5]}
        camera={{ position: [0, 3.0, 11.4], fov: 46, near: 0.5, far: 80 }}
        gl={{ antialias: true, powerPreference: 'high-performance', alpha: true }}
      >
        <color attach="background" args={['#140A1C']} />
        <fog attach="fog" args={['#140A1C', 14, 42]} />

        <ambientLight intensity={0.45} color="#B8A6C2" />
        <pointLight position={[0, 7, 2]} intensity={2.4} color="#FFE9BA" distance={28} />
        <pointLight position={[-10, 6, -8]} intensity={1.8} color="#E83E80" distance={30} />
        <pointLight position={[10, 6, -8]} intensity={1.8} color="#D8B45A" distance={30} />
        <spotLight position={[4, 5, 8]} angle={0.45} penumbra={0.8} intensity={2.2} color="#FFF3D6" />

        <CricketPitchAndBowl />
        <FloodlightTower position={[-11.5, -2.4, -10.5]} aimTarget={[0, -2.2, 0]} beamColor="#D8B45A" />
        <FloodlightTower position={[11.5, -2.4, -10.5]} aimTarget={[0, -2.2, 0]} beamColor="#E83E80" />
        <FloodlightTower position={[-12.5, -2.4, 5.5]} aimTarget={[0, -2.2, 0]} beamColor="#E83E80" />
        <FloodlightTower position={[12.5, -2.4, 5.5]} aimTarget={[0, -2.2, 0]} beamColor="#D8B45A" />

        <HeroCricketBall />
        <AtmosphericParticles />
        <CinematicCameraRig />
      </Canvas>
    </div>
  );
}


import { at } from "../lib/motion";

const PETALS = [
  [350, 236],
  [363.3, 245.7],
  [358.2, 261.3],
  [341.8, 261.3],
  [336.7, 245.7],
];

/** The cover's picture: a small world drawn stroke by stroke as the page loads. */
export function HeroSketch() {
  return (
    <svg
      viewBox="0 0 560 380"
      className="h-auto w-full"
      role="img"
      aria-label="A hand-drawn world: a sun, a cloud raining on a flower, a tree, a car, and a cat"
    >
      <g fill="none" strokeLinecap="round" strokeLinejoin="round">
        <path
          className="draw"
          pathLength={1}
          style={at(0.15, 0.9)}
          d="M24 318C110 310 190 324 280 316S452 308 536 318"
          stroke="#121418"
          strokeWidth={3}
        />
        <circle className="draw" pathLength={1} style={at(0.35, 0.6)} cx={104} cy={92} r={32} stroke="#f2a33a" strokeWidth={4.5} />
        <path
          className="draw"
          pathLength={1}
          style={at(0.75, 0.6)}
          d="M148 92H164M135 123L146 134M104 136V152M73 123L62 134M60 92H44M73 61L62 50M104 48V32M135 61L146 50"
          stroke="#f2a33a"
          strokeWidth={4.5}
        />
        <path
          className="draw"
          pathLength={1}
          style={at(1, 0.8)}
          d="M276 124C252 124 250 94 276 92C276 64 314 56 330 76C342 54 386 56 390 86C418 84 426 124 398 124Z"
          stroke="#5f93d6"
          strokeWidth={4.5}
        />
        <path
          className="draw"
          pathLength={1}
          style={at(1.6, 0.6)}
          d="M300 140L294 160M324 142L318 162M348 140L342 160M372 142L366 162M312 172L306 190M336 174L330 192M360 172L354 190"
          stroke="#5f93d6"
          strokeWidth={3}
        />
        <path
          className="draw"
          pathLength={1}
          style={at(1.8, 0.4)}
          d="M449 316C449 290 451 272 450 254M465 316C465 292 464 274 466 254"
          stroke="#8a6250"
          strokeWidth={4}
        />
        <path
          className="draw"
          pathLength={1}
          style={at(2, 0.7)}
          d="M457 256C425 258 412 228 430 208C422 182 450 166 468 182C486 166 514 182 506 206C524 226 508 258 478 254"
          stroke="#4f8a49"
          strokeWidth={4.5}
        />
        <path
          className="draw"
          pathLength={1}
          style={at(2.4, 0.4)}
          d="M350 316C346 296 354 282 350 262M349 296C334 292 328 282 327 274C340 276 347 284 349 296"
          stroke="#4f8a49"
          strokeWidth={3.5}
        />
        {PETALS.map(([cx, cy], index) => (
          <circle
            key={index}
            className="draw"
            pathLength={1}
            style={at(2.7 + index * 0.06, 0.3)}
            cx={cx}
            cy={cy}
            r={9}
            stroke="#d0558f"
            strokeWidth={3.5}
          />
        ))}
        <circle className="draw" pathLength={1} style={at(3, 0.25)} cx={350} cy={250} r={4.5} stroke="#f2a33a" strokeWidth={3.5} />
        <path
          className="draw"
          pathLength={1}
          style={at(2.9, 0.6)}
          d="M70 306V286H92L108 264H156L174 286H200V306Z"
          stroke="#3f6fa8"
          strokeWidth={4}
        />
        <circle className="draw" pathLength={1} style={at(3.3, 0.3)} cx={98} cy={308} r={11} stroke="#121418" strokeWidth={4} />
        <circle className="draw" pathLength={1} style={at(3.4, 0.3)} cx={172} cy={308} r={11} stroke="#121418" strokeWidth={4} />
        <path
          className="draw"
          pathLength={1}
          style={at(3.5, 0.5)}
          d="M236 316C222 306 224 282 244 278C262 274 274 290 270 316"
          stroke="#8a6250"
          strokeWidth={3.5}
        />
        <circle className="draw" pathLength={1} style={at(3.8, 0.35)} cx={266} cy={264} r={14} stroke="#8a6250" strokeWidth={3.5} />
        <path
          className="draw"
          pathLength={1}
          style={at(4, 0.3)}
          d="M256 254L257 240L265 250M268 250L277 240L278 255M236 310C218 306 214 288 224 278"
          stroke="#8a6250"
          strokeWidth={3.5}
        />
      </g>
      <g className="font-hand" fill="#121418" fontSize={23}>
        <text className="fade" style={at(4.3)} x={178} y={52}>
          suns bring daylight
        </text>
        <text className="fade" style={at(4.6)} x={396} y={40}>
          tap a cloud: rain
        </text>
        <text className="fade" style={at(4.9)} x={84} y={360}>
          cats keep clear of cars
        </text>
      </g>
      <g fill="none" stroke="#121418" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path className="draw" pathLength={1} style={at(4.45, 0.4)} d="M182 60C166 66 154 72 146 82M146 82L157 79M146 82L148 71" />
        <path className="draw" pathLength={1} style={at(4.75, 0.4)} d="M430 48C426 62 418 72 404 78M404 78L415 78M404 78L410 69" />
      </g>
    </svg>
  );
}

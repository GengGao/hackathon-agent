import { useMemo, useState } from "react";

export default function SkeletonText({ lines = 3 }) {
	const widths = ["w-5/6", "w-4/6", "w-3/6", "w-2/3", "w-1/2"];
	const [skeletonId] = useState(() => Math.random().toString(36).slice(2));
	const keys = useMemo(
		() =>
			Array.from({ length: lines }).map(
				() => `${skeletonId}-${Math.random().toString(36).slice(2)}`,
			),
		[lines, skeletonId],
	);

	return (
		<ul className="skeleton-text animate-pulse space-y-2" aria-live="polite">
			{keys.map((key, i) => (
				<li key={key} className={`h-3 rounded ${widths[i % widths.length]}`} />
			))}
		</ul>
	);
}

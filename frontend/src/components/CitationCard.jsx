export default function CitationCard({
    source,
    page,
    snippet,
    score,
    onClick,
  }) {
    return (
      <div
        onClick={onClick}
        className="
          group
          bg-white/[0.04]
          border border-white/10
          hover:border-violet-500/30
          hover:bg-violet-500/[0.06]
          rounded-2xl
          p-4
          transition-all
          duration-200
          cursor-pointer
        "
      >
        {/* Top */}
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex-1 min-w-0">
            <h3
              className="
                text-sm
                font-medium
                text-violet-300
                truncate
                group-hover:text-violet-200
              "
            >
              {source}
            </h3>
  
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-white/35">
                Page {page}
              </span>
  
              {score && (
                <>
                  <span className="text-white/20">•</span>
  
                  <span className="text-xs text-emerald-400">
                    {(score * 100).toFixed(0)}% match
                  </span>
                </>
              )}
            </div>
          </div>
  
          {/* Icon */}
          <div
            className="
              w-9 h-9
              rounded-xl
              bg-violet-500/10
              border border-violet-500/20
              flex items-center justify-center
              shrink-0
            "
          >
            <svg
              className="w-4 h-4 text-violet-300"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M7 8h10M7 12h6m-8 8h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
              />
            </svg>
          </div>
        </div>
  
        {/* Snippet */}
        <p
          className="
            text-sm
            text-white/65
            leading-relaxed
            line-clamp-4
          "
        >
          {snippet}
        </p>
  
        {/* Bottom */}
        <div className="mt-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-white/25">
            <span>Document Source</span>
          </div>
  
          <button
            className="
              text-xs
              text-violet-400
              hover:text-violet-300
              transition-colors
            "
          >
            Open
          </button>
        </div>
      </div>
    );
  }
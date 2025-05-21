import React, { useEffect, useRef } from 'react';

const TerminalLog = ({ log }) => {
  const logRef = useRef(null);

  // Scroll to view when new log appears
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, []);

  return (
    <div ref={logRef} className={`log-entry ${log.type} fade-out`}>
      <span className="log-timestamp">[{log.timestamp}]</span> {log.message}
    </div>
  );
};

export default TerminalLog;

import React from 'react';

interface ProgressIndicatorProps {
  currentStep: number;
  steps: string[];
}

const ProgressIndicator: React.FC<ProgressIndicatorProps> = ({ 
  currentStep, 
  steps 
}) => {
  return (
    <div className="progress-indicator">
      <div className="steps-container">
        {steps.map((step, index) => {
          const stepNumber = index + 1;
          const isCompleted = stepNumber < currentStep;
          const isCurrent = stepNumber === currentStep;

          return (
            <div key={index} className="step-item">
              <div className={`step-circle ${isCompleted ? 'completed' : isCurrent ? 'current' : 'upcoming'}`}>
                {isCompleted ? '✓' : stepNumber}
              </div>
              <div className={`step-label ${isCompleted ? 'completed' : isCurrent ? 'current' : 'upcoming'}`}>
                {step}
              </div>
              {index < steps.length - 1 && (
                <div className={`step-connector ${isCompleted ? 'completed' : ''}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ProgressIndicator;

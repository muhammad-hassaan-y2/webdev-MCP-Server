from .types import SimulationMission, ParamSpec

projectile_range = SimulationMission(
    id="projectile-range",
    title="Predict the range: projectile motion",
    concept="projectile motion & trigonometry in physics",
    description=(
        "Drag the sliders to pick a launch angle and speed, watch the trajectory, "
        "then type your prediction for how far (in meters) it will land. There's "
        "no fixed target - the point is to discover the relationship yourself."
    ),
    params=[
        ParamSpec(key="angle", label="Launch angle", min=5, max=85, step=1, default=45, unit="°"),
        ParamSpec(key="velocity", label="Launch speed", min=5, max=40, step=1, default=20, unit="m/s"),
    ],
    target_label="Predicted range (meters)",
    fallback_hints=[
        "Range depends on both the angle and the speed - the formula is R = v²·sin(2θ)/g.",
        "sin(2θ) is largest when θ = 45°. Try comparing the range at 45° to the range at 30° or 60°.",
        "g ≈ 9.8 m/s² here. If you're computing by hand, make sure your calculator is in degree mode for sin(2θ).",
    ],
)

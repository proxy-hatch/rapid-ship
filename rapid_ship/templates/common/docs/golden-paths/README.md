# Golden paths

Golden paths are worked examples that show an agent how to build a similar, bigger feature, such as another API on an existing server. Each entry points to real code from a merged change.

Golden paths are separate from Patterns:
- A **Pattern** enforces code style or solves smaller recurring problems, with a reference implementation and a check.
- A **Golden path** gives an agent an example when working on similar, bigger problems. It requires no check and no command.

## Library format

The library holds one entry per kind of bigger feature. Each entry describes the feature kind and points to real code from a merged change:

- **Kind of feature:** what this example builds (for example, a new API endpoint or service integration).
- **Merged reference:** paths to real, merged code and pull requests showing how the feature was built and tested.
- **Key takeaways:** what an agent should replicate when building a similar feature.

This library starts empty. As the repository merges new kinds of features, add worked examples here pointing to the merged code.

# world/visuals — offline asset library + runtime compositor
# Usage:
#   from world.visuals.catalog import AssetCatalog
#   from world.visuals.compositor import SceneCompositor
#   from world.visuals.scene_resolver import SceneResolver
#
# Offline (build the library):
#   python -m world.visuals.variant_generator
#
# Runtime (during play):
#   resolver = SceneResolver(catalog)
#   compositor = SceneCompositor(catalog)
#   scene = compositor.compose(resolver.resolve(unified_context))

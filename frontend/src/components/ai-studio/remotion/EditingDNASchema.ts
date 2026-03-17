import { z } from 'zod';

export const LayerSchema = z.object({
  role: z.string(),
  position: z.object({
    top: z.union([z.string(), z.number()]).optional(),
    bottom: z.union([z.string(), z.number()]).optional(),
    left: z.union([z.string(), z.number()]).optional(),
    right: z.union([z.string(), z.number()]).optional(),
    height: z.string(),
    width: z.string(),
  }),
  source_type: z.enum([
    'veo_generated_character', 'veo_generated_environment',
    'video', 'image', 'text_overlay', 'caption', 'empty'
  ]),
  source_url: z.string().optional(),
  z_index: z.number(),
  effects: z.array(z.string()).optional(),
  mask: z.string().optional(),
});

export const EditingDNASchema = z.object({
  layout_id: z.string(),
  meta: z.object({
    composition_type: z.string(),
    aspect_ratio: z.enum(['9:16', '16:9', '1:1']),
    source_reference_id: z.string().optional(),
  }),
  layers: z.array(LayerSchema),
  audio_logic: z.object({
    primary_track: z.string().optional(),
    auto_captions: z.object({
      style: z.string().optional(),
      y_offset: z.string().optional(),
    }).optional(),
  }).optional(),
  timing_dna: z.object({
    hook_duration_frames: z.number().optional(),
    transition_style: z.string().optional(),
    b_roll_frequency: z.string().optional(),
  }).optional(),
});

export type EditingDNA = z.infer<typeof EditingDNASchema>;
export type Layer = z.infer<typeof LayerSchema>;
import { EditingDNA } from './EditingDNASchema';

// Example Editing DNA for a social media video
export const exampleSocialMediaDNA: EditingDNA = {
  layout_id: "social-media-split-v1",
  meta: {
    composition_type: "split_screen_product",
    aspect_ratio: "9:16",
    source_reference_id: "product_123",
  },
  layers: [
    {
      role: "background_video",
      position: {
        top: 0,
        left: 0,
        height: "100%",
        width: "100%",
      },
      source_type: "veo_generated_environment",
      source_url: "/videos/background-kitchen.mp4",
      z_index: 1,
      effects: ["subtle_zoom_in"],
      mask: undefined,
    },
    {
      role: "product_showcase",
      position: {
        top: "20%",
        left: "10%",
        height: "40%",
        width: "80%",
      },
      source_type: "image",
      source_url: "/images/product-hero.jpg",
      z_index: 3,
      effects: ["fade_in"],
      mask: "rounded_corners_lg",
    },
    {
      role: "main_text_title",
      position: {
        top: "70%",
        left: "5%",
        height: "15%",
        width: "90%",
      },
      source_type: "text_overlay",
      source_url: undefined,
      z_index: 5,
      effects: ["fade_in"],
    },
    {
      role: "caption_track",
      position: {
        bottom: "10%",
        left: "5%",
        height: "8%",
        width: "90%",
      },
      source_type: "caption",
      source_url: undefined,
      z_index: 10,
      effects: ["fade_in"],
    },
  ],
  audio_logic: {
    primary_track: "/audio/upbeat-track.mp3",
    auto_captions: {
      style: "bold_white",
      y_offset: "10%",
    },
  },
  timing_dna: {
    hook_duration_frames: 90,  // 3 seconds at 30fps
    transition_style: "smooth_fade",
    b_roll_frequency: "every_10_seconds",
  },
};

// Example for a testimonial video
export const exampleTestimonialDNA: EditingDNA = {
  layout_id: "testimonial-centered-v1",
  meta: {
    composition_type: "testimonial_video",
    aspect_ratio: "16:9",
  },
  layers: [
    {
      role: "speaker_video",
      position: {
        top: "10%",
        left: "20%",
        height: "80%",
        width: "60%",
      },
      source_type: "video",
      source_url: "/videos/speaker-interview.mp4",
      z_index: 2,
      effects: ["subtle_zoom_in"],
      mask: "rounded_corners_sm",
    },
    {
      role: "company_logo",
      position: {
        top: "5%",
        right: "5%",
        height: "10%",
        width: "15%",
      },
      source_type: "image",
      source_url: "/images/company-logo.png",
      z_index: 5,
    },
    {
      role: "quote_text",
      position: {
        bottom: "15%",
        left: "10%",
        height: "20%",
        width: "80%",
      },
      source_type: "text_overlay",
      z_index: 8,
      effects: ["fade_in"],
    },
  ],
  audio_logic: {
    primary_track: "/audio/interview-audio.mp3",
    auto_captions: {
      style: "subtitle_style",
      y_offset: "15%",
    },
  },
};

// Example for a minimal layout
export const exampleMinimalDNA: EditingDNA = {
  layout_id: "minimal-text-v1",
  meta: {
    composition_type: "text_animation",
    aspect_ratio: "1:1",
  },
  layers: [
    {
      role: "main_title",
      position: {
        top: "40%",
        left: "10%",
        height: "20%",
        width: "80%",
      },
      source_type: "text_overlay",
      z_index: 1,
      effects: ["fade_in"],
    },
  ],
  timing_dna: {
    hook_duration_frames: 60,
    transition_style: "instant",
  },
};